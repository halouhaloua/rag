import os
import threading
import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np
import spacy
import torch
import torch.nn.functional as F
import concurrent.futures
from sentence_transformers import SentenceTransformer

from graphrag.models.retriever import utils as retriever_utils
from graphrag.models.retriever.faiss_filter import DualFAISSRetriever
from graphrag.utils import graph_processor
from graphrag.utils import call_llm_api
from graphrag.utils.logger import logger


from graphrag.config import get_config




class KTRetriever:
    def __init__(
        self,
        dataset: str,
        json_path: str = '',
        qa_encoder: Optional[SentenceTransformer] = None,
        device: str = "cuda",
        cache_dir: str = "retriever/faiss_cache_new",
        top_k: int = 5,
        recall_paths: int = 2,
        schema_path: str = '',
        mode: str = "agent",
        config=get_config(),
    ):
        self.config = config

        if config:
            json_path = json_path or config.get_dataset_config(dataset).graph_output
            device = device if device != "cuda" else config.embeddings.device
            cache_dir = (
                cache_dir
                if cache_dir != "retriever/faiss_cache_new"
                else config.retrieval.cache_dir
            )
            top_k = top_k if top_k != 5 else config.retrieval.top_k
            recall_paths = (
                recall_paths if recall_paths != 2 else config.retrieval.recall_paths
            )
            schema_path = schema_path or config.get_dataset_config(dataset).schema_path
            mode = mode if mode != "agent" else config.triggers.mode


        self.graph = graph_processor.load_graph_from_json(json_path)
        self.qa_encoder = config.embeddings.get_model()

        self.llm_client = call_llm_api.LLMCompletionCall()
        self.llm_stream_client = call_llm_api.LLMCompletionCallStream()

        self.device = retriever_utils.resolve_device_str(device)
        logger.info(f"Using device: {self.device}")
        self.cache_dir = cache_dir
        self.top_k = top_k
        self.dataset = dataset
        self.schema_path = schema_path
        self.recall_paths = recall_paths
        self.mode = mode
        os.makedirs(cache_dir, exist_ok=True)
        self.debug_mode = True

        self.nlp = spacy.load(config.nlp.spacy_model)

        self.faiss_retriever = DualFAISSRetriever(
            dataset = dataset,
            model= self.qa_encoder,
            graph=self.graph,
            cache_dir=cache_dir,
            device=self.device,

        )

        self.node_embedding_cache = {}
        self.triple_embedding_cache = {}
        self.query_embedding_cache = {}
        self.faiss_search_cache = {}
        self.chunk_embedding_cache = {}
        self.chunk_faiss_index = None
        self.chunk_id_to_index = {}
        self.index_to_chunk_id = {}
        self.chunk_embeddings_precomputed = False

        self.cache_locks = {
            "node_embedding": threading.RLock(),
            "triple_embedding": threading.RLock(),
            "query_embedding": threading.RLock(),
            "chunk_embedding": threading.RLock(),
        }

        self.node_embeddings_precomputed = False
        self.precompute_lock = threading.Lock()

        self.chunk2id = {}
        chunk_file = config.output.chunks_dir + f"/{self.dataset}.txt"
        if os.path.exists(chunk_file):
            try:
                with open(chunk_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and "\t" in line:
                            parts = line.split("\t", 1)
                            if (
                                len(parts) == 2
                                and parts[0].startswith("id: ")
                                and parts[1].startswith("Chunk: ")
                            ):
                                chunk_id = parts[0][4:]
                                chunk_text = parts[1][7:]
                                self.chunk2id[chunk_id] = chunk_text
                logger.info(f"Loaded {len(self.chunk2id)} chunks from {chunk_file}")
            except Exception as e:
                logger.error(f"Error loading chunks from {chunk_file}: {e}")
                self.chunk2id = {}

        self._node_text_index = {}
        self.use_exact_keyword_matching = (
            True  # Set to False for original substring matching
        )
        self.enable_performance_optimizations = True
        self._node_text_cache = {}

        self._relation_bonus_keywords = {
            "is", "was", "has", "had", "contains", "located", "born", "died"
        }

        if self.enable_performance_optimizations:
            try:
                cache_loaded = self._load_node_embedding_cache()
                self._precompute_node_texts()
                self._build_node_text_index()
                self._precompute_chunk_embeddings()

                if cache_loaded:
                    self.node_embeddings_precomputed = True

                    if (
                        not hasattr(self.faiss_retriever, "node_embedding_cache")
                        or not self.faiss_retriever.node_embedding_cache
                    ):
                        self.faiss_retriever.node_embedding_cache = {}
                        for node, embed in self.node_embedding_cache.items():
                            self.faiss_retriever.node_embedding_cache[node] = (
                                embed.clone().detach()
                            )

            except Exception:
                self.enable_performance_optimizations = False

    def build_indices(self):
        """Build all FAISS indices for efficient retrieval."""
        self.faiss_retriever.build_indices()
        self._precompute_node_embeddings()

    def _get_query_embedding(self, query: str) -> torch.Tensor:
        """
        Get query embedding with simple caching (most expensive operation)
        """
        query_embed = (
            torch.tensor(self.qa_encoder.encode(query)).float().to(self.device)
        )
        return query_embed

    def _precompute_node_texts(self):
        """
        Precompute node texts for all nodes to avoid repeated text extraction.
        This is called during initialization to build the text cache.
        """
        if self._load_node_text_cache():
            return

        start_time = time.time()

        all_nodes = list(self.graph.nodes())
        processed_nodes = 0

        for node in all_nodes:
            try:
                node_text = self._get_node_text(node)
                if retriever_utils.is_valid_node_text(node_text):
                    self._node_text_cache[node] = node_text
                processed_nodes += 1

            except Exception:
                continue

        end_time = time.time()
        logger.info(
            f"Node texts precomputed for {len(self._node_text_cache)} nodes in {end_time - start_time:.2f} seconds"
        )

        try:
            self._save_node_text_cache()
        except Exception as e:
            logger.warning(f"Failed to save node text cache: {type(e).__name__}: {e}")

    def _save_node_text_cache(self):
        return retriever_utils.save_pickle_cache(
            self._node_text_cache, self.cache_dir, self.dataset, "node_text_cache", logger=logger
        )

    def _load_node_text_cache(self):
        expected_keys = set(self.graph.nodes())
        cache = retriever_utils.load_pickle_cache(
            self.cache_dir, self.dataset, "node_text_cache", expected_keys=expected_keys, logger=logger
        )
        if cache is not None:
            self._node_text_cache = cache
            return True
        self._node_text_cache = {}
        return False

    def _check_cache_consistency(self, cache_dict: dict, name: str) -> bool:
        current_nodes = set(self.graph.nodes())
        return retriever_utils.check_cache_consistency_simple(
            current_nodes, cache_dict, name=name, logger=logger
        )

    def _precompute_node_embeddings(self):
        """
        Precompute embeddings for all nodes to avoid repeated encoding
        """
        with self.precompute_lock:
            if self.node_embeddings_precomputed:
                return

            if self._load_node_embedding_cache():
                self.node_embeddings_precomputed = True
                return

            if (
                hasattr(self.faiss_retriever, "node_embedding_cache")
                and self.faiss_retriever.node_embedding_cache
            ):
                for node, embed in self.faiss_retriever.node_embedding_cache.items():
                    self.node_embedding_cache[node] = embed.clone().detach()
                self.node_embeddings_precomputed = True
                logger.info(
                    f"Successfully loaded {len(self.node_embedding_cache)} node embeddings from faiss_retriever cache"
                )

                self._save_node_embedding_cache()
                return

            logger.warning("No cache found, computing embeddings from scratch...")

            all_nodes = list(self.graph.nodes())
            batch_size = 100
            if self.config:
                batch_size = self.config.embeddings.batch_size * 3

            total_processed = 0
            for i in range(0, len(all_nodes), batch_size):
                batch_nodes = all_nodes[i : i + batch_size]
                batch_texts = []
                valid_nodes = []

                for node in batch_nodes:
                    try:
                        node_text = self._get_node_text(node)
                        if retriever_utils.is_valid_node_text(node_text):
                            batch_texts.append(node_text)
                            valid_nodes.append(node)
                    except Exception as e:
                        logger.error(f"Error getting text for node {node}: {str(e)}")
                        continue

                if batch_texts:
                    try:
                        batch_embeddings = self.qa_encoder.encode(
                            batch_texts, convert_to_tensor=True
                        )

                        for j, node in enumerate(valid_nodes):
                            self.node_embedding_cache[node] = batch_embeddings[j]
                            total_processed += 1

                    except Exception as e:
                        logger.error(
                            f"Error encoding batch {i // batch_size}: {str(e)}"
                        )
                        for node in valid_nodes:
                            try:
                                node_text = self._get_node_text(node)
                                if retriever_utils.is_valid_node_text(node_text):
                                    embedding = (
                                        torch.tensor(self.qa_encoder.encode(node_text))
                                        .float()
                                        .to(self.device)
                                    )
                                    self.node_embedding_cache[node] = embedding
                                    total_processed += 1
                            except Exception as e2:
                                logger.error(f"Error encoding node {node}: {str(e2)}")
                                continue

            self.node_embeddings_precomputed = True
            logger.info(
                f"Node embeddings precomputed for {total_processed} nodes (cache size: {len(self.node_embedding_cache)})"
            )

            try:
                self._save_node_embedding_cache()
            except Exception as e:
                logger.warning(f"Failed to save node embedding cache: {e}")
                logger.info("Continuing without saving cache...")

            self._cleanup_node_cache()

    def _save_node_embedding_cache(self):
        path = f"{self.cache_dir}/{self.dataset}/node_embedding_cache.pt"
        if not self.node_embedding_cache:
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return retriever_utils.save_embedding_cache(self.node_embedding_cache, path, logger=logger)

    def _load_node_embedding_cache(self):
        path = f"{self.cache_dir}/{self.dataset}/node_embedding_cache.pt"
        cache = retriever_utils.load_embedding_cache(path, self.device, logger=logger)
        if cache is None:
            return False
        if not self._check_cache_consistency(cache, "Embedding cache"):
            return False
        self.node_embedding_cache.clear()
        self.node_embedding_cache.update(cache)
        return True

    def _cleanup_node_cache(self):
        """
        Clean up node embedding cache to save memory
        """
        with self.cache_locks["node_embedding"]:
            retriever_utils.evict_lru_cache(
                self.node_embedding_cache, 5000, strategy="recent"
            )

    def retrieve(self, question: str):
        """
        Perform enhanced two-path retrieval process with query understanding and caching.

        Args:
            question: Query question

        Returns:
            Dictionary containing:
            - path1_results: Results from node/relation embedding retrieval with 1-hop triples
            - path2_results: Results from triple-only retrieval
            - chunk_ids: Set of chunk IDs from all retrieved nodes
        """
        start_time = time.time()

        question_embed = self._get_query_embedding(question)
        query_time = time.time() - start_time

        all_chunk_ids = set()

        if self.recall_paths == 1:
            path_start = time.time()
            path1_results = self._node_relation_retrieval(question_embed, question)
            path1_time = time.time() - path_start
            logger.info(
                f"Query encoding: {query_time:.3f}s, Path1 retrieval: {path1_time:.3f}s"
            )

            path1_chunk_ids = self._extract_chunk_ids_from_nodes(
                path1_results["top_nodes"]
            )
            all_chunk_ids.update(path1_chunk_ids)

            if "chunk_results" in path1_results and path1_results["chunk_results"]:
                chunk_chunk_ids = set(
                    path1_results["chunk_results"].get("chunk_ids", [])
                )
                all_chunk_ids.update(chunk_chunk_ids)

            limited_chunk_ids = list(all_chunk_ids)

            result = {"path1_results": path1_results, "chunk_ids": limited_chunk_ids}
        else:
            parallel_start = time.time()
            result = self._parallel_dual_path_retrieval(question_embed, question)
            parallel_time = time.time() - parallel_start
            logger.info(
                f"Query encoding: {query_time:.3f}s, Parallel retrieval: {parallel_time:.3f}s"
            )

        return question_embed, result

    def retrieve_with_type_filtering(
        self, question: str, involved_types: dict = {}
    ):
        """
        Enhanced retrieval with type-based filtering followed by similarity search.

        Args:
            question: Query question
            involved_types: Dictionary containing involved schema types

        Returns:
            Dictionary containing filtered retrieval results
        """
        start_time = time.time()

        question_embed = self._get_query_embedding(question)
        query_time = time.time() - start_time

        if involved_types and any(
            involved_types.get(k, []) for k in ["nodes", "relations", "attributes"]
        ):
            # Use type-based filtering path
            type_start = time.time()
            type_filtered_results = self._type_based_retrieval(
                question_embed, question, involved_types
            )
            type_filtering_time = time.time() - type_start
            logger.info(
                f"Query encoding: {query_time:.3f}s, Type-based retrieval: {type_filtering_time:.3f}s"
            )

            return question_embed, type_filtered_results
        else:
            question_embed, original_results = self.retrieve(question)
            logger.info(
                f"Query encoding: {query_time:.3f}s, Fallback to original retrieval"
            )
            return question_embed, original_results

    def _type_based_retrieval(
        self, question_embed: torch.Tensor, question: str, involved_types: dict
    ) -> Dict:
        """
        Perform hybrid retrieval: type-filtered node_relation path + original other paths.

        Args:
            question_embed: Question embedding tensor
            question: Original question text
            involved_types: Dictionary with node types, relations, and attributes

        Returns:
            Dictionary containing hybrid retrieval results
        """
        if self.recall_paths == 1:
            # Single path: only filter node_relation path
            filtered_results = self._type_filtered_node_relation_retrieval(
                question_embed, question, involved_types
            )
            return filtered_results
        else:
            # Multi-path: filter only node_relation, keep others original
            hybrid_results = self._hybrid_type_filtered_retrieval(
                question_embed, question, involved_types
            )
            return hybrid_results

    def _type_filtered_node_relation_retrieval(
        self, question_embed: torch.Tensor, question: str, involved_types: dict
    ) -> Dict:
        """
        Single path retrieval with type filtering only on node_relation path.
        """
        target_node_types = involved_types.get("nodes", [])

        type_filtered_nodes = self._filter_nodes_by_schema_type(target_node_types)

        if type_filtered_nodes:
            filtered_node_results = self._similarity_search_on_filtered_nodes(
                question_embed, type_filtered_nodes
            )

            one_hop_triples = self._get_one_hop_triples_from_nodes(
                filtered_node_results["top_nodes"]
            )

            chunk_ids = self._extract_chunk_ids_from_nodes(
                filtered_node_results["top_nodes"]
            )

            result = {
                "path1_results": {
                    "top_nodes": filtered_node_results["top_nodes"],
                    "one_hop_triples": one_hop_triples,
                },
                "chunk_ids": list(chunk_ids),
            }
        else:
            result = self._node_relation_retrieval(question_embed, question)

        return result

    def _hybrid_type_filtered_retrieval(
        self, question_embed: torch.Tensor, question: str, involved_types: dict
    ) -> Dict:
        """
        Multi-path retrieval: type-filtered node_relation + original other paths.
        """
        target_node_types = involved_types.get("nodes", [])

        # Path 1: Type-filtered node_relation retrieval
        if target_node_types:
            type_filtered_nodes = self._filter_nodes_by_schema_type(target_node_types)
            if type_filtered_nodes:
                path1_results = self._type_filtered_node_relation_path(
                    question_embed, type_filtered_nodes
                )
            else:
                path1_results = self._node_relation_retrieval(question_embed, question)
        else:
            path1_results = self._node_relation_retrieval(question_embed, question)

        # Path 2: triple-only retrieval
        path2_results = self._triple_only_retrieval(question_embed)

        all_chunk_ids = set()
        path1_chunk_ids = self._extract_chunk_ids_from_nodes(path1_results["top_nodes"])
        all_chunk_ids.update(path1_chunk_ids)

        if "chunk_results" in path2_results and path2_results["chunk_results"]:
            chunk_chunk_ids = set(path2_results["chunk_results"].get("chunk_ids", []))
            all_chunk_ids.update(chunk_chunk_ids)

        result = {
            "path1_results": path1_results,
            "path2_results": path2_results,
            "chunk_ids": list(all_chunk_ids),
        }

        return result

    def _type_filtered_node_relation_path(
        self, question_embed: torch.Tensor, filtered_nodes: list
    ) -> Dict:
        """
        Execute type-filtered node_relation path.
        """
        filtered_node_results = self._similarity_search_on_filtered_nodes(
            question_embed, filtered_nodes
        )

        one_hop_triples = self._get_one_hop_triples_from_nodes(
            filtered_node_results["top_nodes"]
        )

        return {
            "top_nodes": filtered_node_results["top_nodes"],
            "one_hop_triples": one_hop_triples,
        }

    def _similarity_search_on_filtered_nodes(
        self, question_embed: torch.Tensor, filtered_nodes: list
    ) -> Dict:
        """
        Perform similarity search only on filtered nodes.
        """
        if not filtered_nodes:
            return {"top_nodes": []}

        filtered_node_embeddings = []
        filtered_node_map = {}

        for idx, node_id in enumerate(filtered_nodes):
            if node_id in self.faiss_retriever.node_map.values():
                # Find the original index of this node in the FAISS index
                original_idx = None
                for orig_idx, orig_node_id in self.faiss_retriever.node_map.items():
                    if orig_node_id == node_id:
                        original_idx = orig_idx
                        break

                if original_idx is not None:
                    node_embedding = self.faiss_retriever.node_index.reconstruct(
                        int(original_idx)
                    )
                    filtered_node_embeddings.append(node_embedding)
                    filtered_node_map[len(filtered_node_embeddings) - 1] = node_id

        if filtered_node_embeddings:
            filtered_embeddings_array = np.array(filtered_node_embeddings).astype(
                "float32"
            )
            temp_index = faiss.IndexFlatIP(filtered_embeddings_array.shape[1])
            temp_index.add(filtered_embeddings_array)

            search_k = min(self.top_k, len(filtered_node_embeddings))
            _, indices = temp_index.search(question_embed.reshape(1, -1), search_k)

            top_filtered_nodes = [
                filtered_node_map[idx] for idx in indices[0] if idx in filtered_node_map
            ]
        else:
            top_filtered_nodes = filtered_nodes[: self.top_k]

        return {"top_nodes": top_filtered_nodes}

    def _get_one_hop_triples_from_nodes(self, node_list: list) -> list:

        one_hop_triples = []
        node_set = set(node_list)

        for u, v, data in self.graph.edges(data=True):
            if u in node_set or v in node_set:
                relation = data.get("relation", "")
                u_name = self._get_node_name(u)
                v_name = self._get_node_name(v)
                one_hop_triples.append((u_name, relation, v_name))

        return one_hop_triples[: self.top_k]

    def _filter_nodes_by_schema_type(self, target_types: list) -> list:
        """
        Filter nodes based on their schema_type property.

        Args:
            target_types: List of target schema types

        Returns:
            List of filtered node IDs
        """
        if not target_types:
            return list(self.graph.nodes())

        filtered_nodes = []
        for node_id, node_data in self.graph.nodes(data=True):
            node_properties = node_data.get("properties", {})
            node_schema_type = node_properties.get("schema_type", "")

            if node_schema_type in target_types:
                filtered_nodes.append(node_id)
            # Also include nodes without schema_type for backward compatibility
            elif not node_schema_type and node_data.get("label") == "entity":
                filtered_nodes.append(node_id)

        return filtered_nodes

    def _get_node_name(self, node_id: str) -> str:
        """Get the name property of a node."""
        node_data = self.graph.nodes.get(node_id, {})
        properties = node_data.get("properties", {})
        return properties.get("name", node_id)

    def _parallel_dual_path_retrieval(
        self, question_embed: torch.Tensor, question: str
    ) -> Dict:
        all_chunk_ids = set()
        start_time = time.time()

        max_workers = 4
        if self.config:
            max_workers = self.config.retrieval.faiss.max_workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            path1_future = executor.submit(
                self._node_relation_retrieval, question_embed, question
            )
            path2_future = executor.submit(self._triple_only_retrieval, question_embed)

            path1_results = path1_future.result()
            path2_results = path2_future.result()

        start_time = time.time()

        path1_chunk_ids = self._extract_chunk_ids_from_nodes(path1_results["top_nodes"])
        path2_chunk_ids = self._extract_chunk_ids_from_triple_nodes(
            path2_results["scored_triples"]
        )

        path3_chunk_ids = set()
        if "chunk_results" in path1_results and path1_results["chunk_results"]:
            path3_chunk_ids = set(path1_results["chunk_results"].get("chunk_ids", []))

        all_chunk_ids.update(path1_chunk_ids)
        all_chunk_ids.update(path2_chunk_ids)
        all_chunk_ids.update(path3_chunk_ids)

        limited_chunk_ids = list(all_chunk_ids)[: self.top_k]

        end_time = time.time()
        logger.info(f"Time taken to extract chunk IDs: {end_time - start_time} seconds")
        return {
            "path1_results": path1_results,
            "path2_results": path2_results,
            "chunk_ids": limited_chunk_ids,
        }

    def _node_relation_retrieval(
        self, question_embed: torch.Tensor, question: str = ""
    ) -> Dict:
        max_workers = 4
        if self.config:
            max_workers = self.config.retrieval.faiss.max_workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            q_embed = question_embed
            search_k = min(self.top_k * 3, 50)

            future_faiss_nodes = executor.submit(
                self._execute_faiss_node_search, q_embed.cpu().numpy(), search_k
            )

            future_keywords = future_keyword_nodes = None
            if question:
                future_keywords = executor.submit(
                    self._extract_query_keywords, question
                )
                future_keyword_nodes = executor.submit(
                    self._get_keyword_based_nodes, future_keywords
                )

            future_faiss_relations = executor.submit(
                self._execute_faiss_relation_search, q_embed.cpu().numpy()
            )

            future_chunk_retrieval = executor.submit(
                self._chunk_embedding_retrieval, question_embed, self.top_k
            )

            faiss_candidate_nodes = future_faiss_nodes.result()

            future_faiss_sim = executor.submit(
                self._batch_calculate_entity_similarities,
                question_embed,
                faiss_candidate_nodes,
            )

            keyword_candidate_nodes = []
            if future_keyword_nodes:
                keyword_nodes = future_keyword_nodes.result()
                existing_faiss_nodes = set(faiss_candidate_nodes)
                keyword_candidate_nodes = [
                    n for n in keyword_nodes if n not in existing_faiss_nodes
                ]

            future_keyword_sim = (
                executor.submit(
                    self._batch_calculate_entity_similarities,
                    question_embed,
                    keyword_candidate_nodes,
                )
                if keyword_candidate_nodes
                else None
            )

            candidate_nodes = []
            faiss_similarities = future_faiss_sim.result()

            candidate_nodes.extend(
                (node, sim) for node, sim in faiss_similarities.items()
            )

            if future_keyword_sim:
                keyword_similarities = future_keyword_sim.result()

                candidate_nodes.extend(
                    (node, sim)
                    for node, sim in keyword_similarities.items()
                    if sim > 0.05
                )

            candidate_nodes.sort(key=lambda x: x[1], reverse=True)
            top_nodes = [
                node for node, score in candidate_nodes[: self.top_k] if score > 0.05
            ]

            all_relations = future_faiss_relations.result()

            future_path_triples = (
                executor.submit(
                    self._path_based_search,
                    top_nodes,
                    future_keywords.result() if future_keywords else [],
                    max_depth=2,
                )
                if question
                else None
            )

            future_neighbor_triples = executor.submit(
                self._optimized_neighbor_expansion, top_nodes, question_embed
            )

            one_hop_triples = future_neighbor_triples.result()
            path_triples = future_path_triples.result() if future_path_triples else []
            relation_triples = self._get_relation_matched_triples(
                top_nodes, all_relations
            )

            all_triples = list(
                {triple for triple in one_hop_triples + path_triples + relation_triples}
            )
            chunk_results = future_chunk_retrieval.result()

        return {
            "top_nodes": top_nodes,
            "top_relations": all_relations,
            "one_hop_triples": all_triples,
            "chunk_results": chunk_results,
        }

    def _execute_faiss_node_search(self, q_embed, search_k: int) -> List[str]:
        _, I_nodes = self.faiss_retriever.node_index.search(
            q_embed.reshape(1, -1), search_k
        )
        return [
            self.faiss_retriever.node_map[str(idx)]
            for idx in I_nodes[0]
            if idx != -1 and str(idx) in self.faiss_retriever.node_map
        ]

    def _execute_faiss_relation_search(self, q_embed) -> List[str]:
        _, I_relations = self.faiss_retriever.relation_index.search(
            q_embed.reshape(1, -1), self.top_k
        )
        return [
            self.faiss_retriever.relation_map[str(idx)]
            for idx in I_relations[0]
            if idx != -1 and str(idx) in self.faiss_retriever.relation_map
        ]

    def _get_keyword_based_nodes(self, future_keywords) -> List[str]:
        keywords = future_keywords.result()
        return self._keyword_based_node_search(keywords)

    @lru_cache(maxsize=1000)
    def _get_cached_neighbors(self, node_id: str) -> List[str]:
        return list(self.graph.neighbors(node_id))

    def _optimized_neighbor_expansion(
        self, top_nodes: List[str], question_embed: torch.Tensor
    ) -> List[Tuple]:
        all_neighbors = set()
        edge_queries = set()
        for node in top_nodes:
            neighbors = self._get_cached_neighbors(node)
            all_neighbors.update(n for n in neighbors)
            edge_queries.update((node, n) for n in all_neighbors)
            edge_queries.update((n, node) for n in all_neighbors)

        triples = []
        for u, v in edge_queries:
            edge_data = self.graph.get_edge_data(u, v)
            if edge_data:
                relation = list(edge_data.values())[0].get("relation", "")
                if relation:
                    triples.append((u, relation, v))
        return triples

    def _get_relation_matched_triples(
        self, top_nodes: List[str], relations: List[str]
    ) -> List[Tuple]:

        top_node_set = set(top_nodes)
        relation_set = set(relations)

        return [
            (u, data.get("relation"), v)
            for u, v, data in self.graph.edges(data=True)
            if data.get("relation") in relation_set
            and (u in top_node_set or v in top_node_set)
        ]

    def _triple_only_retrieval(self, question_embed: torch.Tensor) -> Dict:
        """
        Path 2: Triple-only retrieval to get top 10 related triples from FAISS.

        Args:
            question_embed: Encoded question tensor

        Returns:
            Dictionary containing:
            - scored_triples: List of (head, relation, tail, score) tuples
        """
        try:
            faiss_results = self.faiss_retriever.dual_path_retrieval(
                question_embed, top_k=self.top_k
            )

            scored_triples = faiss_results.get("scored_triples", [])

            return {"scored_triples": scored_triples}
        except Exception as e:
            logger.error(f"Error in _triple_only_retrieval: {str(e)}")
            return {"scored_triples": []}

    def _get_node_text(self, node: str) -> str:
        if node in self._node_text_cache:
            return self._node_text_cache[node]
        if node not in self.graph.nodes:
            return f"[Unknown Node: {node}]"
        data = self.graph.nodes[node]
        name, description = retriever_utils.extract_node_name_and_description(data)
        result = f"{name} {description}".strip()
        if not result:
            result = f"[Node: {node}]"
        self._node_text_cache[node] = result
        return result

    def _get_node_properties(self, node: str) -> str:
        """
        Get formatted properties of a node for display.

        Args:
            node: Node ID in the graph

        Returns:
            Formatted string representation of node properties
        """
        if node not in self.graph.nodes:
            return ""

        data = self.graph.nodes[node]
        properties = []

        SKIP_FIELDS = retriever_utils.SCHEMA_SKIP_FIELDS

        for source in [data.get("properties", {}), data]:
            if not isinstance(source, dict):
                continue
            for key, value in source.items():
                if key in SKIP_FIELDS:
                    continue
                value_str = (
                    ", ".join(map(str, value))
                    if isinstance(value, list)
                    else str(value)
                )
                properties.append(f"{key}: {value_str}")

        return f"[{', '.join(properties)}]" if properties else ""


    def _process_chunk_results(
        self, chunk_results: Dict, question_embed: torch.Tensor, top_k: int
    ) -> Tuple[List[str], set]:
        """Process chunk results and return formatted results and chunk IDs."""
        if not chunk_results:
            return [], set()

        reranked_results = self._rerank_chunks_by_relevance(
            chunk_results, question_embed, top_k
        )
        chunk_ids = reranked_results.get("chunk_ids", [])
        chunk_scores = reranked_results.get("scores", [])
        chunk_contents = reranked_results.get("chunk_contents", [])

        formatted_results = []
        chunk_id_set = set()

        for chunk_id, score, content in zip(chunk_ids, chunk_scores, chunk_contents):
            formatted_result = (
                f"[Chunk {chunk_id}] {content[:200]}... [score: {score:.3f}]"
            )
            formatted_results.append(formatted_result)
            chunk_id_set.add(chunk_id)

        return formatted_results, chunk_id_set

    def _collect_all_scored_triples(
        self, results: Dict, question_embed: torch.Tensor
    ) -> List[Tuple[str, str, str, float]]:
        """Collect and merge all scored triples from both paths."""
        all_scored_triples = []

        # Add path2 scored triples if available
        path2_scored = results["path2_results"].get("scored_triples", [])
        if path2_scored:
            all_scored_triples.extend(path2_scored)

        # Add path1 reranked triples
        path1_triples = results["path1_results"].get("one_hop_triples", [])
        if path1_triples:
            path1_scored = self._rerank_triples_by_relevance(
                path1_triples, question_embed
            )
            all_scored_triples.extend(path1_scored)

        # Sort by score (descending) and return top k
        all_scored_triples.sort(key=lambda x: x[3], reverse=True)
        return all_scored_triples

    def _format_scored_triples(
        self, scored_triples: List[Tuple[str, str, str, float]]
    ) -> List[str]:
        """Format scored triples into readable text with node properties."""
        formatted_triples = []

        for h, r, t, score in scored_triples:
            head_text = self._get_node_text(h)
            tail_text = self._get_node_text(t)

            if not retriever_utils.is_valid_node_text(head_text) or not retriever_utils.is_valid_node_text(tail_text):
                continue

            head_props = self._get_node_properties(h)
            tail_props = self._get_node_properties(t)
            triple_text = f"({head_text} {head_props}, {r}, {tail_text} {tail_props}) [score: {score:.3f}]"
            if "represented_by" == r or "kw_filter_by" == r:
                continue
            formatted_triples.append(triple_text)

        return formatted_triples

    def _extract_chunk_ids_from_triples(
        self, scored_triples: List[Tuple[str, str, str, float]]
    ) -> set:
        return self._extract_chunk_ids_from_triple_nodes(scored_triples)

    def _get_node_chunk_id(self, node_data: dict) -> str | None:
        """Extract chunk ID from node data, handling both old and new structures."""
        if isinstance(node_data.get("properties"), dict):
            return node_data["properties"].get("chunk id")
        return node_data.get("chunk id")

    def _get_matching_chunks(self, chunk_ids: set) -> List[str]:
        """Get chunk contents for given chunk IDs."""
        return [
            self.chunk2id[chunk_id]
            for chunk_id in chunk_ids
            if chunk_id in self.chunk2id
        ]

    def process_retrieval_results(
        self, question: str, top_k: int = 20, involved_types: dict = {}
    ) -> Tuple[Dict, float]:
        """Process retrieval results with optimized structure and helper methods."""
        start_time = time.time()

        if involved_types:
            question_embed, results = self.retrieve_with_type_filtering(
                question, involved_types
            )
        else:
            question_embed, results = self.retrieve(question)

        retrieval_time = time.time() - start_time
        logger.info(f"retrieval time: {retrieval_time:.4f}")

        chunk_results = results["path1_results"].get("chunk_results")
        chunk_retrieval_results, chunk_retrieval_ids = self._process_chunk_results(
            chunk_results, question_embed, top_k
        )

        all_scored_triples = self._collect_all_scored_triples(results, question_embed)
        limited_scored_triples = all_scored_triples[:top_k]

        # Format triples and extract chunk IDs
        formatted_triples = self._format_scored_triples(limited_scored_triples)
        triple_chunk_ids = self._extract_chunk_ids_from_triples(limited_scored_triples)

        all_chunk_ids = chunk_retrieval_ids | triple_chunk_ids
        matching_chunks = self._get_matching_chunks(all_chunk_ids)

        retrieval_results = {
            "triples": formatted_triples,
            "chunk_ids": list(all_chunk_ids),
            "chunk_contents": matching_chunks,
            "chunk_retrieval_results": chunk_retrieval_results,
        }

        return retrieval_results, retrieval_time

    def _process_single_subquestion(
        self, sub_question: Dict, top_k: int, involved_types: dict = {}
    ) -> Dict:

        sub_question_text = sub_question.get("sub-question", "")
        try:
            retrieval_results, time_taken = self.process_retrieval_results(
                sub_question_text, top_k, involved_types
            )
            triples = retrieval_results.get("triples", []) or []
            chunk_ids = retrieval_results.get("chunk_ids", []) or []
            chunk_contents = retrieval_results.get("chunk_contents", []) or []

            if isinstance(chunk_contents, dict):
                chunk_contents_list = list(chunk_contents.values())
            else:
                chunk_contents_list = chunk_contents

            if not isinstance(triples, (list, tuple)):
                logger.warning(f"triples is not a list: {type(triples)}")
                triples = []
            if not isinstance(chunk_ids, (list, tuple)):
                logger.warning(f"chunk_ids is not a list: {type(chunk_ids)}")
                chunk_ids = []
            if not isinstance(chunk_contents_list, (list, tuple)):
                logger.warning(
                    f"chunk_contents_list is not a list: {type(chunk_contents_list)}"
                )
                chunk_contents_list = []

            sub_result = {
                "sub_question": sub_question_text,
                "triples_count": len(triples),
                "chunk_ids_count": len(chunk_ids),
                "time_taken": time_taken,
            }

            chunk_contents_dict = {}
            for i, chunk_id in enumerate(chunk_ids):
                if i < len(chunk_contents_list):
                    chunk_contents_dict[chunk_id] = chunk_contents_list[i]
                else:
                    chunk_contents_dict[chunk_id] = (
                        f"[Missing content for chunk {chunk_id}]"
                    )

            return {
                "triples": set(triples),
                "chunk_ids": set(chunk_ids),
                "chunk_contents": chunk_contents_dict,
                "sub_result": sub_result,
            }

        except Exception as e:
            logger.error(
                f"Error processing sub-question '{sub_question_text}': {str(e)}"
            )
            return {
                "triples": set(),
                "chunk_ids": set(),
                "chunk_contents": {},
                "sub_result": {
                    "sub_question": sub_question_text,
                    "triples_count": 0,
                    "chunk_ids_count": 0,
                    "time_taken": 0.0,
                },
            }

    def generate_prompt(self, question: str, sub_question: list, context: str) -> str:

        if self.config:
            if self.dataset == "novel":
                return self.config.get_prompt_formatted(
                    "retrieval", "novel_chs", question=question, context=context
                )
            elif self.dataset == "novel_eng":
                return self.config.get_prompt_formatted(
                    "retrieval", "novel_eng", question=question, context=context
                )
            else:
                return self.config.get_prompt_formatted(
                    "retrieval", "general", question=question, context=context
                )
        else:
            if self.dataset == "novel":
                prompt = f"""
                你是小说知识助手，你的任务是根据提供的小说知识库回答问题。
                1. 如果知识库中的信息不足以回答问题，请根据你的推理和知识回答。
                2. 回答要简洁明了。
                3. 对于事实性问题，提供具体的事实或人物名称。
                4. 对于时间性问题，提供具体的时间、年份或时间段。
                问题：{question}
                相关知识：{context}
                答案（简洁明了）：
                """
            elif self.dataset == "novel_eng":
                prompt = f"""
                You are a novel knowledge assistant. Your task is to answer the question based on the provided novel knowledge context.
                1. If the knowledge is insufficient, answer the question based on your own knowledge.
                2. Be precise and concise in your answer.
                3. For factual questions, provide the specific fact or entity name
                4. For temporal questions, provide the specific date, year, or time period

                Question: {question}
                
                The question is broken down into sub-question to help thinking:{sub_question}

                Knowledge Context:
                {context}   

                Answer (be specific and direct):
                """
            else:
                prompt = f"""
                You are an expert knowledge assistant. Your task is to answer the question based on the provided knowledge context.

                1. Use ONLY the information from the provided knowledge context and try your best to answer the question.
                2. If the knowledge is insufficient, reject to answer the question.
                3. Be precise and concise in your answer
                4. For factual questions, provide the specific fact or entity name
                5. For temporal questions, provide the specific date, year, or time period
                
                The question is broken down into sub-question to help thinking:{sub_question}

                Question: {question}

                Knowledge Context:
                {context}

                Answer (be specific and direct):
                """
            return prompt

    def generate_answer(self, prompt: str) -> str:
        answer = self.llm_client.call_api(prompt)
        logger.info("Retrieved context:")
        logger.info(prompt)
        logger.info(f"Answer: {answer}")
        return answer

    async def generate_answer_stream(self, prompt: str):
        logger.info("Retrieved context:")
        logger.info(prompt)
        async for token in self.llm_stream_client.call_api_stream(prompt):
            yield token

    def _extract_chunk_ids_from_nodes(self, nodes: List[str]) -> set:
        chunk_ids = set()
        for node in nodes:
            if node in self.graph.nodes:
                chunk_id = self._get_node_chunk_id(self.graph.nodes[node])
                if chunk_id:
                    chunk_ids.add(str(chunk_id))
        return chunk_ids

    def _extract_chunk_ids_from_triple_nodes(
        self, scored_triples: List[Tuple[str, str, str, float]]
    ) -> set:
        nodes = [n for t in scored_triples for n in (t[0], t[2]) if n in self.graph.nodes]
        return self._extract_chunk_ids_from_nodes(nodes)


    def _calculate_entity_similarity(
        self, query_embed: torch.Tensor, node: str
    ) -> float:
        """
        Calculate entity-level similarity between query and node.
        With caching for performance optimization.

        Args:
            query_embed: Query embedding
            node: Node ID

        Returns:
            Similarity score
        """

        try:
            if node not in self.graph.nodes:
                return 0.0

            node_text = self._get_node_text(node)
            if not retriever_utils.is_valid_node_text(node_text):
                return 0.0

            if node in self.node_embedding_cache:
                node_embed = self.node_embedding_cache[node]
            else:
                node_embed = (
                    torch.tensor(self.qa_encoder.encode(node_text))
                    .float()
                    .to(self.device)
                )
                self.node_embedding_cache[node] = node_embed

            similarity = F.cosine_similarity(query_embed, node_embed, dim=0).item()
            similarity = max(0.0, similarity)

            return similarity

        except Exception as e:
            logger.error(
                f"Error calculating entity similarity for node {node}: {str(e)}"
            )
            return 0.0

    def _batch_calculate_entity_similarities(
        self, query_embed: torch.Tensor, nodes: List[str]
    ) -> Dict[str, float]:
        node_embeddings = []
        valid_nodes = []
        with self.cache_locks["node_embedding"]:
            for node in nodes:
                if node in self.node_embedding_cache:
                    node_embeddings.append(self.node_embedding_cache[node])
                    valid_nodes.append(node)

        if node_embeddings:
            try:
                return retriever_utils.batch_compute_similarities(
                    query_embed, node_embeddings, valid_nodes
                )
            except Exception:
                similarities = {}
                for node in valid_nodes:
                    try:
                        similarities[node] = self._calculate_entity_similarity(query_embed, node)
                    except Exception as e2:
                        logger.error(f"Error calculating similarity for node {node}: {str(e2)}")
                return similarities

        similarities = {}
        for node in nodes:
            try:
                similarities[node] = self._calculate_entity_similarity(query_embed, node)
            except Exception as e:
                logger.error(f"Error calculating similarity for node {node}: {str(e)}")
        return similarities

    def _build_triple_text(
        self, h: str, r: str, t: str
    ) -> tuple[str | None, tuple | None]:
        try:
            head_text = self._get_node_text(h)
            tail_text = self._get_node_text(t)
            if not retriever_utils.is_valid_node_text(head_text) or not retriever_utils.is_valid_node_text(tail_text):
                return None, None
            return f"{head_text} {r} {tail_text}", (h, r, t)
        except Exception as e:
            logger.error(f"Error processing triple ({h}, {r}, {t}): {str(e)}")
            return None, None

    def _compute_triple_score(self, similarity: float, r: str) -> float:
        relation_bonus = 0.1 if r.lower() in self._relation_bonus_keywords else 0.0
        return max(0.0, similarity + relation_bonus)

    def _rerank_triples_by_relevance(
        self, triples: List[Tuple[str, str, str]], question_embed: torch.Tensor
    ) -> List[Tuple[str, str, str, float]]:
        start_time = time.time()
        if not triples:
            return []

        triple_texts = []
        valid_triples = []

        for h, r, t in triples:
            triple_text, valid = self._build_triple_text(h, r, t)
            if valid:
                triple_texts.append(triple_text)
                valid_triples.append(valid)

        if not valid_triples:
            return []

        try:
            encode_start = time.time()
            triple_embeddings = self.qa_encoder.encode(
                triple_texts, convert_to_tensor=True
            ).to(self.device)
            logger.info(
                f"[StepTiming] step=batch_encode_triple_texts time={time.time() - encode_start:.4f}"
            )

            sim_calc_start = time.time()
            similarities = F.cosine_similarity(
                question_embed.unsqueeze(0), triple_embeddings, dim=1
            )
            logger.info(
                f"[StepTiming] step=batch_calculate_similarities time={time.time() - sim_calc_start:.4f}"
            )

            scored_triples = []
            for i, (h, r, t) in enumerate(valid_triples):
                final_score = self._compute_triple_score(similarities[i].item(), r)
                if final_score > 0.05:
                    scored_triples.append((h, r, t, final_score))

        except Exception as e:
            logger.error(f"Error in batch triple encoding: {str(e)}")
            return self._rerank_triples_individual(triples, question_embed)

        scored_triples.sort(key=lambda x: x[3], reverse=True)
        logger.info(
            f"[StepTiming] step=_rerank_triples_by_relevance time={time.time() - start_time:.4f}"
        )
        return scored_triples

    def _rerank_triples_individual(
        self, triples: List[Tuple[str, str, str]], question_embed: torch.Tensor
    ) -> List[Tuple[str, str, str, float]]:
        scored_triples = []

        for h, r, t in triples:
            triple_text, valid = self._build_triple_text(h, r, t)
            if not valid:
                continue
            try:
                triple_embed = (
                    torch.tensor(self.qa_encoder.encode(triple_text))
                    .float()
                    .to(self.device)
                )
                similarity = F.cosine_similarity(
                    question_embed, triple_embed, dim=0
                ).item()
                final_score = self._compute_triple_score(similarity, r)
                if final_score > 0.05:
                    scored_triples.append((h, r, t, final_score))
            except Exception as e:
                logger.error(f"Error reranking triple ({h}, {r}, {t}): {str(e)}")
                continue

        scored_triples.sort(key=lambda x: x[3], reverse=True)
        return scored_triples

    def _extract_query_keywords(self, question: str) -> List[str]:
        """
        Automatically extract keywords from the question using spaCy NER and POS tagging.
        Optimized for single-query scenarios.

        Args:
            question: Input question

        Returns:
            List of automatically discovered keywords
        """
        try:
            doc = self.nlp(question.lower())
            keywords = []

            for token in doc:
                if not token.is_stop and len(token.text) > 2:
                    if token.ent_type_:
                        keywords.append(token.text.lower())
                    elif token.pos_ in ["NOUN", "PROPN", "ADJ"]:
                        keywords.append(token.text.lower())
                    elif token.pos_ == "VERB":
                        keywords.append(token.text.lower())

            for ent in doc.ents:
                if len(ent.text) > 2:
                    keywords.append(ent.text.lower())

            unique_keywords = list(set(keywords))
            return unique_keywords

        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []

    def _keyword_based_node_search(self, keywords: List[str]) -> List[str]:
        """
        Optimized keyword-based node search with text indexing and early termination.
        Optimized for single-query scenarios.
        """
        if not keywords:
            return []

        use_exact_matching = getattr(self, "use_exact_keyword_matching", True)

        if use_exact_matching:
            if not hasattr(self, "_node_text_index") or self._node_text_index is None:
                logger.warning(
                    "Node text index not found. This should be built during initialization."
                )
                return []

            relevant_nodes = set()
            max_nodes_per_keyword = 50

            for keyword in keywords:
                if keyword in self._node_text_index:
                    keyword_nodes = self._node_text_index[keyword]
                    if len(keyword_nodes) > max_nodes_per_keyword:
                        keyword_nodes = set(list(keyword_nodes)[:max_nodes_per_keyword])
                    relevant_nodes.update(keyword_nodes)
                else:
                    continue

                if len(relevant_nodes) > 200:
                    break
            return list(relevant_nodes)
        else:
            # Fallback: linear substring matching
            relevant_nodes = []
            for node in self.graph.nodes():
                try:
                    node_text = self._get_node_text(node).lower()
                    for keyword in keywords:
                        if keyword in node_text:
                            relevant_nodes.append(node)
                            break
                except Exception:
                    continue
            return relevant_nodes

    def _build_node_text_index(self):
        """
        Build inverted index for node texts to speed up keyword search.
        Optimized to use precomputed node texts and persistent caching.
        """
        if self._load_node_text_index():
            logger.info("Loaded node text index from cache")
            return

        start_time = time.time()
        logger.info("Building optimized node text index for keyword search...")
        self._node_text_index = {}

        if hasattr(self, "_node_text_cache") and self._node_text_cache:
            node_texts = self._node_text_cache
        else:
            node_texts = {}
            for node in self.graph.nodes():
                node_texts[node] = self._get_node_text(node)

        total_nodes = len(node_texts)
        processed_nodes = 0

        for node, node_text in node_texts.items():
            try:
                node_text_lower = node_text.lower()
                words = set(node_text_lower.split())

                for word in words:
                    if len(word) > 2:
                        if word not in self._node_text_index:
                            self._node_text_index[word] = set()
                        self._node_text_index[word].add(node)

                processed_nodes += 1
                if processed_nodes % 1000 == 0:
                    logger.info(f"Indexed {processed_nodes}/{total_nodes} nodes")

            except Exception as e:
                logger.error(f"Error indexing node {node}: {str(e)}")
                continue

        end_time = time.time()
        logger.info(
            f"Time taken to build node text index: {end_time - start_time} seconds"
        )

        self._save_node_text_index()

    def _save_node_text_index(self):
        if not self._node_text_index:
            return False
        serialized = {w: list(n) for w, n in self._node_text_index.items()}
        return retriever_utils.save_pickle_cache(
            serialized, self.cache_dir, self.dataset, "node_text_index", logger=logger
        )

    def _load_node_text_index(self):
        serialized = retriever_utils.load_pickle_cache(
            self.cache_dir, self.dataset, "node_text_index", logger=logger
        )
        if serialized is None:
            return False
        self._node_text_index: dict = {w: set(n) for w, n in serialized.items()}
        if not self._check_text_index_consistency():
            return False
        return True

    def _check_text_index_consistency(self):
        indexed_nodes = set()
        for nodes in self._node_text_index.values():
            indexed_nodes.update(nodes)
        return self._check_cache_consistency(
            {n: True for n in indexed_nodes}, "Text index"
        )

    def _path_based_search(
        self, start_nodes: List[str], target_keywords: List[str], max_depth: int = 2
    ) -> List[Tuple[str, str, str]]:
        """
        Search for paths from start nodes to nodes containing target keywords.

        Args:
            start_nodes: Starting node IDs
            target_keywords: Keywords to search for
            max_depth: Maximum path depth

        Returns:
            List of triples found along the paths
        """
        found_triples = []
        visited = set()

        def dfs_search(node: str, depth: int, path: List[str]):
            if depth > max_depth or node in visited:
                return

            visited.add(node)

            try:
                node_text = self._get_node_text(node).lower()
                for keyword in target_keywords:
                    if keyword in node_text:
                        for i in range(len(path) - 1):
                            u, v = path[i], path[i + 1]
                            edge_data = self.graph.get_edge_data(u, v)
                            if edge_data and "relation" in edge_data:
                                relation = list(edge_data.values())[0]["relation"]
                                found_triples.append((u, relation, v))
                        break
            except Exception as e:
                logger.warning(
                    f"Error during DFS path search at node {start_node if 'start_node' in locals() else ''}: {type(e).__name__}: {e}"
                )

            if depth < max_depth:
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        dfs_search(neighbor, depth + 1, path + [neighbor])

        for start_node in start_nodes:
            dfs_search(start_node, 0, [start_node])
        return found_triples

    def _precompute_chunk_embeddings(self):
        """
        Precompute embeddings for all chunks to enable direct chunk retrieval
        """
        with self.precompute_lock:
            if self.chunk_embeddings_precomputed:
                return

            logger.info("Precomputing chunk embeddings for direct chunk retrieval...")
            if self._load_chunk_embedding_cache():
                logger.info("Successfully loaded chunk embeddings from disk cache")
                self.chunk_embeddings_precomputed = True
                return

            if not self.chunk2id:
                logger.info("Warning: No chunks available for embedding computation")
                return

            logger.info("Computing chunk embeddings from scratch...")

            chunk_ids = list(self.chunk2id.keys())
            chunk_texts = list(self.chunk2id.values())
            batch_size = 50
            if self.config:
                batch_size = self.config.embeddings.batch_size

            total_processed = 0
            embeddings_list = []
            valid_chunk_ids = []

            for i in range(0, len(chunk_texts), batch_size):
                batch_texts = chunk_texts[i : i + batch_size]
                batch_chunk_ids = chunk_ids[i : i + batch_size]

                try:
                    batch_embeddings = self.qa_encoder.encode(
                        batch_texts, convert_to_tensor=True
                    )

                    for j, chunk_id in enumerate(batch_chunk_ids):
                        self.chunk_embedding_cache[chunk_id] = batch_embeddings[j]
                        embeddings_list.append(batch_embeddings[j].cpu().numpy())
                        valid_chunk_ids.append(chunk_id)
                        total_processed += 1

                except Exception as e:
                    logger.error(
                        f"Error encoding chunk batch {i // batch_size}: {str(e)}"
                    )
                    for j, chunk_id in enumerate(batch_chunk_ids):
                        try:
                            chunk_text = self.chunk2id[chunk_id]
                            embedding = (
                                torch.tensor(self.qa_encoder.encode(chunk_text))
                                .float()
                                .to(self.device)
                            )
                            self.chunk_embedding_cache[chunk_id] = embedding
                            embeddings_list.append(embedding.cpu().numpy())
                            valid_chunk_ids.append(chunk_id)
                            total_processed += 1
                        except Exception as e2:
                            logger.error(f"Error encoding chunk {chunk_id}: {str(e2)}")
                            continue

            if embeddings_list:
                try:
                    logger.info("Building FAISS index for chunk embeddings...")
                    embeddings_array = np.array(embeddings_list)
                    dimension = embeddings_array.shape[1]

                    self.chunk_faiss_index = faiss.IndexFlatIP(
                        dimension
                    )  # Inner product for cosine similarity
                    self.chunk_faiss_index.add(embeddings_array.astype("float32"))

                    for i, chunk_id in enumerate(valid_chunk_ids):
                        self.chunk_id_to_index[chunk_id] = i
                        self.index_to_chunk_id[i] = chunk_id

                    logger.info(f"FAISS index built with {len(valid_chunk_ids)} chunks")

                except Exception as e:
                    logger.error(f"Error building FAISS index for chunks: {str(e)}")

            self.chunk_embeddings_precomputed = True
            logger.info(
                f"Chunk embeddings precomputed for {total_processed} chunks (cache size: {len(self.chunk_embedding_cache)})"
            )

            self._save_chunk_embedding_cache()

    def _save_chunk_embedding_cache(self):
        """Save chunk embedding cache to disk"""
        cache_path = f"{self.cache_dir}/{self.dataset}/chunk_embedding_cache.pt"
        if not self.chunk_embedding_cache:
            return False
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        return retriever_utils.save_embedding_cache(
            self.chunk_embedding_cache, cache_path, logger=logger
        )

    def _load_chunk_embedding_cache(self):
        """Load chunk embedding cache from disk"""
        cache_path = f"{self.cache_dir}/{self.dataset}/chunk_embedding_cache.pt"
        cache = retriever_utils.load_embedding_cache(
            cache_path, self.device, logger=logger
        )
        if cache is None:
            return False

        self.chunk_embedding_cache.clear()
        self.chunk_embedding_cache.update(cache)

        if self.chunk_embedding_cache:
            try:
                embeddings_list = []
                valid_chunk_ids = []
                for chunk_id, embed in self.chunk_embedding_cache.items():
                    embeddings_list.append(embed.cpu().numpy())
                    valid_chunk_ids.append(chunk_id)

                embeddings_array = np.array(embeddings_list)
                dimension = embeddings_array.shape[1]
                self.chunk_faiss_index = faiss.IndexFlatIP(dimension)
                self.chunk_faiss_index.add(embeddings_array.astype("float32"))

                self.chunk_id_to_index.clear()
                self.index_to_chunk_id.clear()
                for i, chunk_id in enumerate(valid_chunk_ids):
                    self.chunk_id_to_index[chunk_id] = i
                    self.index_to_chunk_id[i] = chunk_id
            except Exception:
                return False

        if not self._check_chunk_cache_consistency():
            return False

        return True

    def _check_chunk_cache_consistency(self):
        current_keys = set(self.chunk2id.keys())
        return retriever_utils.check_cache_consistency_simple(
            current_keys, self.chunk_embedding_cache, name="Chunk cache", logger=logger
        )

    def _chunk_embedding_retrieval(
        self, question_embed: torch.Tensor, top_k: int = 20
    ) -> Dict:
        try:
            if not self.chunk_embeddings_precomputed or self.chunk_faiss_index is None:
                logger.info(
                    "Warning: Chunk embeddings not precomputed, skipping chunk retrieval"
                )
                return {"chunk_ids": [], "scores": [], "chunk_contents": []}

            query_embed_np = (
                question_embed.cpu().numpy().reshape(1, -1).astype("float32")
            )
            scores, indices = self.chunk_faiss_index.search(
                query_embed_np, min(top_k, self.chunk_faiss_index.ntotal)
            )

            chunk_ids = []
            similarity_scores = []
            chunk_contents = []

            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx != -1 and idx in self.index_to_chunk_id:
                    chunk_id = self.index_to_chunk_id[idx]
                    chunk_ids.append(chunk_id)
                    similarity_scores.append(float(score))

                    if chunk_id in self.chunk2id:
                        chunk_contents.append(self.chunk2id[chunk_id])
                    else:
                        chunk_contents.append(f"[Missing content for chunk {chunk_id}]")

            return {
                "chunk_ids": chunk_ids,
                "scores": similarity_scores,
                "chunk_contents": chunk_contents,
            }

        except Exception as e:
            logger.error(f"Error in chunk embedding retrieval: {str(e)}")
            return {"chunk_ids": [], "scores": [], "chunk_contents": []}

    def _rerank_chunks_by_relevance(
        self, chunk_results: Dict, question_embed: torch.Tensor, top_k: int = 10
    ) -> Dict:
        """
        Rerank chunks by relevance to the question using semantic similarity

        Args:
            chunk_results: Dictionary containing chunk_ids, scores, and chunk_contents
            question_embed: Query embedding tensor
            top_k: Number of top chunks to return

        Returns:
            Reranked chunk results with updated scores
        """
        try:
            chunk_ids = chunk_results.get("chunk_ids", [])
            original_scores = chunk_results.get("scores", [])
            chunk_contents = chunk_results.get("chunk_contents", [])

            if not chunk_ids or not chunk_contents:
                return chunk_results

            chunk_similarities = []
            for i, (chunk_id, content) in enumerate(zip(chunk_ids, chunk_contents)):
                try:
                    chunk_embed = (
                        torch.tensor(self.qa_encoder.encode(content))
                        .float()
                        .to(self.device)
                    )

                    similarity = F.cosine_similarity(
                        question_embed, chunk_embed, dim=0
                    ).item()
                    similarity = max(0.0, similarity)  # Ensure non-negative

                    faiss_score = (
                        original_scores[i] if i < len(original_scores) else 0.0
                    )
                    combined_score = (
                        faiss_score + similarity
                    ) / 2.0  # Average of both scores

                    chunk_similarities.append((chunk_id, content, combined_score, i))

                except Exception as e:
                    logger.error(
                        f"Error calculating similarity for chunk {chunk_id}: {str(e)}"
                    )
                    faiss_score = (
                        original_scores[i] if i < len(original_scores) else 0.0
                    )
                    chunk_similarities.append((chunk_id, content, faiss_score, i))

            chunk_similarities.sort(key=lambda x: x[2], reverse=True)

            top_chunks = chunk_similarities[:top_k]

            reranked_chunk_ids = [chunk_id for chunk_id, _, _, _ in top_chunks]
            reranked_scores = [score for _, _, score, _ in top_chunks]
            reranked_contents = [content for _, content, _, _ in top_chunks]

            return {
                "chunk_ids": reranked_chunk_ids,
                "scores": reranked_scores,
                "chunk_contents": reranked_contents,
            }

        except Exception as e:
            logger.error(f"Error in chunk reranking: {str(e)}")
            return chunk_results
