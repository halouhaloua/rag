import json
import os
import threading
import time
from concurrent import futures
from typing import Any, Dict, List, Tuple

import nanoid
import networkx as nx
import tiktoken
import json_repair

from graphrag.config import get_config
from graphrag.models.constructor import tree_comm
from graphrag.utils import call_llm_api, graph_processor
from graphrag.utils.logger import logger


def load_schema(schema_path=None, schema_data=None) -> Dict[str, Any]:
    if schema_data is not None:
        return schema_data
    if schema_path:
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
                return schema
        except FileNotFoundError:
            return dict()
    return dict()


def _split_text_with_overlap(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    min_tail_tokens: int = 100,
) -> List[str]:
    """Split text into chunks with overlap using token count."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = tiktoken.get_encoding("gpt5")

    tokens = encoding.encode(text)
    if len(tokens) <= chunk_size:
        return [text]

    windows = []
    start = 0
    step = chunk_size - overlap
    if step <= 0:
        step = chunk_size  # Prevent infinite loop if overlap >= chunk_size

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        windows.append([start, end])
        start += step

    if len(windows) >= 2:
        idx = 0
        while idx < len(windows):
            cur_len = windows[idx][1] - windows[idx][0]
            if cur_len < min_tail_tokens:
                if idx > 0:
                    windows[idx - 1][1] = windows[idx][1]
                    windows.pop(idx)
                    continue
                elif idx + 1 < len(windows):
                    windows[idx + 1][0] = windows[idx][0]
                    windows.pop(idx)
                    continue
            idx += 1

    chunks = []
    for s, e in windows:
        decoded_chunk = encoding.decode(tokens[s:e])
        if (e - s < 5) or (len(decoded_chunk.strip()) < 5):
            continue
        chunks.append(decoded_chunk)
    return chunks


def token_cal(text: str):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def _validate_triple_format(triple: list) -> tuple:
    """Validate and normalize triple format, returning (subject, predicate, object) or None."""
    try:
        if len(triple) > 3:
            triple = triple[:3]
        elif len(triple) < 3:
            return None

        return tuple(triple)
    except Exception:
        return None


class KTBuilder:
    def __init__(self, dataset_name, schema_path=None, mode=None, config=None, schema_data=None):
        if config is None:
            config = get_config()

        self.config = config
        self.dataset_name = dataset_name
        self.schema = load_schema(
            schema_path or config.get_dataset_config(dataset_name).schema_path,
            schema_data,
        )
        self.graph = nx.MultiDiGraph()
        self.node_counter = 0
        self.datasets_no_chunk = config.construction.datasets_no_chunk
        self.token_len = 0
        self.lock = threading.Lock()
        self.llm_client = call_llm_api.LLMCompletionCall()
        self.all_chunks = {}
        self.mode = mode or config.construction.mode

    def chunk_text(self, text) -> Tuple[List[str], Dict[str, str]]:
        if self.dataset_name in self.datasets_no_chunk:
            chunks = [
                f"{text.get('title', '')} {text.get('text', '')}".strip()
                if isinstance(text, dict)
                else str(text)
            ]
        else:
            # Use configured chunk size and overlap
            raw_text = str(text)
            if isinstance(text, dict):
                raw_text = f"{text.get('title', '')} {text.get('text', '')}".strip()

            chunk_size = getattr(self.config.construction, "chunk_size", 1000)
            overlap = getattr(self.config.construction, "overlap", 200)
            min_tail_tokens = getattr(self.config.construction, "min_tail_tokens", 100)
            chunks = _split_text_with_overlap(
                raw_text, chunk_size, overlap, min_tail_tokens
            )

        chunk2id = {}
        for chunk in chunks:
            try:
                chunk_id = nanoid.generate(size=8)
                chunk2id[chunk_id] = chunk
            except Exception as e:
                logger.warning(
                    f"Failed to generate chunk id with nanoid: {type(e).__name__}: {e}"
                )

        with self.lock:
            self.all_chunks.update(chunk2id)

        return chunks, chunk2id

    def extract_with_llm(self, prompt: str):
        response = self.llm_client.call_api(prompt)
        parsed_dict = json_repair.loads(response)
        parsed_json = json.dumps(parsed_dict, ensure_ascii=False)
        return parsed_json

    def _get_construction_prompt(self, chunk: str) -> str:
        """Get the appropriate construction prompt based on dataset name and mode (agent/noagent)."""
        recommend_schema = json.dumps(self.schema, ensure_ascii=False)

        # Base prompt type mapping
        prompt_type_map = {"novel": "novel", "novel_eng": "novel_eng"}

        base_prompt_type = prompt_type_map.get(self.dataset_name, "general")

        # Add agent suffix if in agent mode
        if self.mode == "agent":
            prompt_type = f"{base_prompt_type}_agent"
        else:
            prompt_type = base_prompt_type

        return self.config.get_prompt_formatted(
            "construction", prompt_type, schema=recommend_schema, chunk=chunk
        )

    def _validate_and_parse_llm_response(self, prompt: str, llm_response: str) -> dict | None:
        """Validate and parse LLM response, returning None if invalid."""
        if llm_response is None:
            return None

        try:
            self.token_len += token_cal(prompt + llm_response)
            return json_repair.loads(llm_response)
        except Exception:
            return None

    def _find_or_create_entity(
        self, entity_name: str, chunk_id: int, entity_type: str = None
    ) -> str:
        entity_node_id = next(
            (
                n
                for n, d in self.graph.nodes(data=True)
                if d.get("label") == "entity" and d["properties"]["name"] == entity_name
            ),
            None,
        )

        if not entity_node_id:
            entity_node_id = f"entity_{self.node_counter}"
            properties = {"name": entity_name, "chunk id": chunk_id}
            if entity_type:
                properties["schema_type"] = entity_type

            self.graph.add_node(
                entity_node_id, label="entity", properties=properties, level=2
            )
            self.node_counter += 1

        return entity_node_id

    def _process_attributes(
        self, extracted_attr: dict, chunk_id: int, entity_types: dict = {}
    ):
        for entity, attributes in extracted_attr.items():
            for attr in attributes:
                attr_node_id = f"attr_{self.node_counter}"
                self.graph.add_node(
                    attr_node_id,
                    label="attribute",
                    properties={"name": attr, "chunk id": chunk_id},
                    level=1,
                )
                self.node_counter += 1

                entity_type = entity_types.get(entity) if entity_types else None
                entity_node_id = self._find_or_create_entity(
                    entity, chunk_id, entity_type
                )
                self.graph.add_edge(
                    entity_node_id, attr_node_id, relation="has_attribute"
                )

    def _process_triples(
        self, extracted_triples: list, chunk_id: int, entity_types: dict = {}
    ):
        for triple in extracted_triples:
            validated_triple = _validate_triple_format(triple)
            if not validated_triple:
                continue

            subj, pred, obj = validated_triple

            subj_type = entity_types.get(subj) if entity_types else None
            obj_type = entity_types.get(obj) if entity_types else None

            subj_node_id = self._find_or_create_entity(subj, chunk_id, subj_type)
            obj_node_id = self._find_or_create_entity(obj, chunk_id, obj_type)

            self.graph.add_edge(subj_node_id, obj_node_id, relation=pred)

    def process_level1_level2(self, chunk: str, chunk_id: int):
        prompt = self._get_construction_prompt(chunk)
        llm_response = self.extract_with_llm(prompt)

        parsed_response = self._validate_and_parse_llm_response(prompt, llm_response)
        if not parsed_response:
            return

        if self.mode == "agent":
            new_schema_types = parsed_response.get("new_schema_types", {})
            if new_schema_types:
                self._update_schema_with_new_types(new_schema_types)

        extracted_attr = parsed_response.get("attributes", {})
        extracted_triples = parsed_response.get("triples", [])
        entity_types = parsed_response.get("entity_types", {})

        with self.lock:
            self._process_attributes(extracted_attr, chunk_id, entity_types)
            self._process_triples(extracted_triples, chunk_id, entity_types)

    def _update_schema_with_new_types(self, new_schema_types: Dict[str, List[str]]):
        """Update the schema file with new types discovered by the agent.

        This method processes schema evolution suggestions from the LLM and updates
        the corresponding schema file with new node types, relations, and attributes.
        Only adds types that don't already exist in the current schema.

        Args:
            new_schema_types: Dictionary containing 'nodes', 'relations', and 'attributes' lists
        """
        try:
            schema_paths = {
                "hotpot": "schemas/hotpot.json",
                "2wiki": "schemas/2wiki.json",
                "musique": "schemas/musique.json",
                "novel": "schemas/novels_chs.json",
                "graphrag-bench": "schemas/graphrag-bench.json",
            }

            schema_path = schema_paths.get(self.dataset_name)
            if not schema_path:
                return

            with open(schema_path, "r", encoding="utf-8") as f:
                current_schema = json.load(f)

            updated = False

            if "nodes" in new_schema_types:
                for new_node in new_schema_types["nodes"]:
                    if new_node not in current_schema.get("Nodes", []):
                        current_schema.setdefault("Nodes", []).append(new_node)
                        updated = True

            if "relations" in new_schema_types:
                for new_relation in new_schema_types["relations"]:
                    if new_relation not in current_schema.get("Relations", []):
                        current_schema.setdefault("Relations", []).append(new_relation)
                        updated = True

            if "attributes" in new_schema_types:
                for new_attribute in new_schema_types["attributes"]:
                    if new_attribute not in current_schema.get("Attributes", []):
                        current_schema.setdefault("Attributes", []).append(
                            new_attribute
                        )
                        updated = True

            # Save updated schema back to file
            if updated:
                with open(schema_path, "w", encoding="utf-8") as f:
                    json.dump(current_schema, f, ensure_ascii=False, indent=2)

                # Update the in-memory schema
                self.schema = current_schema

        except Exception as e:
            logger.error(
                f"Failed to update schema for dataset '{self.dataset_name}': {type(e).__name__}: {e}"
            )

    def process_level4(self):
        """Process communities using Tree-Comm algorithm"""
        level2_nodes = [n for n, d in self.graph.nodes(data=True) if d["level"] == 2]
        start_comm = time.time()
        _tree_comm = tree_comm.FastTreeComm(
            self.graph,
            struct_weight=self.config.tree_comm.struct_weight,
        )
        comm_to_nodes = _tree_comm.detect_communities(level2_nodes)

        # create super nodes (level 4 communities)
        _tree_comm.create_super_nodes_with_keywords(comm_to_nodes, level=4)
        # _tree_comm.add_keywords_to_level3(comm_to_nodes)
        # connect keywords to communities (optional)
        end_comm = time.time()
        logger.info(f"Community Indexing Time: {end_comm - start_comm}s")


    def process_document(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single document and return its results."""
        try:
            if not doc:
                raise ValueError("Document is empty or None")

            chunks, chunk2id = self.chunk_text(doc)

            if not chunks or not chunk2id:
                raise ValueError(
                    f"No valid chunks generated from document. Chunks: {len(chunks)}, Chunk2ID: {len(chunk2id)}"
                )

            for chunk in chunks:
                try:
                    id = next(key for key, value in chunk2id.items() if value == chunk)
                except StopIteration:
                    id = nanoid.generate(size=8)
                    chunk2id[id] = chunk

                self.process_level1_level2(chunk, id)

        except Exception as e:
            error_msg = f"Error processing document: {type(e).__name__}: {str(e)}"
            raise Exception(error_msg) from e

    def process_all_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Process all documents with high concurrency and pass results to process_level4."""

        max_workers = min(
            self.config.construction.max_workers, (os.cpu_count() or 1) + 4
        )
        start_construct = time.time()
        total_docs = len(documents)

        logger.info(
            f"Starting processing {total_docs} documents with {max_workers} workers..."
        )

        all_futures = []
        processed_count = 0
        failed_count = 0

        try:
            with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all documents for processing and store futures
                all_futures = [
                    executor.submit(self.process_document, doc) for doc in documents
                ]

                for i, future in enumerate(futures.as_completed(all_futures)):
                    try:
                        future.result()
                        processed_count += 1

                        if processed_count % 5 == 0 or processed_count == total_docs:
                            elapsed_time = time.time() - start_construct
                            avg_time_per_doc = (
                                elapsed_time / processed_count
                                if processed_count > 0
                                else 0
                            )
                            remaining_docs = total_docs - processed_count
                            estimated_remaining_time = remaining_docs * avg_time_per_doc

                            logger.info(
                                f"Progress: {processed_count}/{total_docs} documents processed "
                                f"({processed_count / total_docs * 100:.1f}%) "
                                f"[{failed_count} failed] "
                                f"ETA: {estimated_remaining_time / 60:.1f} minutes"
                            )

                    except Exception:
                        failed_count += 1

        except Exception:
            return

        end_construct = time.time()
        logger.info(f"Construction Time: {end_construct - start_construct}s")
        logger.info(f"Successfully processed: {processed_count}/{total_docs} documents")
        logger.info(f"Failed: {failed_count} documents")

        logger.info(f"🚀🚀🚀🚀 {'Processing Level 3 and 4':^20} 🚀🚀🚀🚀")
        logger.info(f"{'➖' * 20}")
        self.triple_deduplicate()
        self.process_level4()

    def triple_deduplicate(self):
        """deduplicate triples in lv1 and lv2"""
        new_graph = nx.MultiDiGraph()

        for node, node_data in self.graph.nodes(data=True):
            new_graph.add_node(node, **node_data)

        seen_triples = set()
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            relation = data.get("relation")
            if (u, v, relation) not in seen_triples:
                seen_triples.add((u, v, relation))
                new_graph.add_edge(u, v, **data)
        self.graph = new_graph

    def format_output(self) -> List[Dict[str, Any]]:
        """convert graph to specified output format"""
        output = []

        for u, v, data in self.graph.edges(data=True):
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]

            relationship = {
                "start_node": {
                    "label": u_data["label"],
                    "properties": u_data["properties"],
                },
                "relation": data["relation"],
                "end_node": {
                    "label": v_data["label"],
                    "properties": v_data["properties"],
                },
            }
            output.append(relationship)

        return output

    def save_graphml(self, output_path: str):
        graph_processor.save_graph(self.graph, output_path)

    def build_knowledge_graph(self, corpus):
        logger.info(f"========{'Start Building':^20}========")
        logger.info(f"{'➖' * 30}")

        with open(corpus, "r", encoding="utf-8") as f:
            documents = json_repair.load(f)

        self.process_all_documents(documents)

        logger.info(f"All Process finished, token cost: {self.token_len}")

        output = self.format_output()
        return output
