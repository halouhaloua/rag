"""
Configuration loader and manager for KT-RAG framework.
Handles loading, validation, and access to configuration parameters.
"""

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from graphrag.config.prompts import prompts
from graphrag.utils.logger import logger
from sentence_transformers import SentenceTransformer

model_path = Path(__file__).parent.parent.parent / "dir"
model = SentenceTransformer(str(model_path))


file_path = Path(__file__).parent.parent

@dataclass
class DatasetConfig:
    corpus_path: str
    qa_path: str
    schema_path: str
    graph_output: str


@dataclass
class TriggersConfig:
    constructor_trigger: bool = True
    retrieve_trigger: bool = True
    mode: str = "agent"


@dataclass
class ConstructionConfig:
    mode: str = "agent"
    max_workers: int = 5
    datasets_no_chunk: list = None
    chunk_size: int = 1000
    overlap: int = 50


@dataclass
class TreeCommConfig:
    embedding_model = model
    struct_weight: float = 0.3
    enable_fast_mode: bool = True


@dataclass
class FAISSConfig:
    search_k: int = 50
    max_workers: int = 4
    device: str = "gpu"


@dataclass
class AgentConfig:
    max_steps: int = 5
    enable_ircot: bool = False
    enable_parallel_subquestions: bool = True


@dataclass
class RetrievalConfig:
    top_k: int = 5
    recall_paths: int = 2
    top_k_filter: int = 20
    similarity_threshold: float = 0.3
    enable_query_enhancement: bool = True
    enable_reranking: bool = True
    enable_high_recall: bool = True
    enable_caching: bool = True
    cache_dir: str = str(file_path / "retriever/faiss_cache_new")
    faiss: FAISSConfig = None
    agent: AgentConfig = None

    def __post_init__(self):
        if self.faiss is None:
            self.faiss = FAISSConfig()
        if self.agent is None:
            self.agent = AgentConfig()


@dataclass
class EmbeddingsConfig:
    model = model
    device: str = "cuda"
    batch_size: int = 32
    max_length: int = 512


@dataclass
class NLPConfig:
    spacy_model: str = "en_core_web_lg"
    spacy_model_zh: str = "zh_core_web_lg"


@dataclass
class OutputConfig:
    base_dir: str = str(file_path / "output")
    graphs_dir: str = str(file_path / "output/graphs")
    chunks_dir: str = str(file_path / "output/chunks")
    logs_dir: str = str(file_path / "output/logs")
    save_intermediate_results: bool = True
    save_chunk_details: bool = True


@dataclass
class PerformanceConfig:
    parallel_processing: bool = True
    max_workers: int = 32
    batch_size: int = 16
    memory_optimization: bool = True


class ConfigManager:
    def __init__(self):
        self.datasets: Dict[str, DatasetConfig] = {
            "demo": DatasetConfig(
                corpus_path="",
                qa_path="",
                schema_path=str(file_path / "schemas/demo.json"),
                graph_output=str(file_path / "output/graphs/demo_new.json"),
            )
        }
        self.prompts: Dict[str, Any] = prompts
        self.triggers = TriggersConfig()
        self.construction = ConstructionConfig()
        self.tree_comm = TreeCommConfig()
        self.retrieval = RetrievalConfig()
        self.embeddings = EmbeddingsConfig()
        self.nlp = NLPConfig()
        self.output = OutputConfig()
        self.performance = PerformanceConfig()
        self.retrieval.faiss = FAISSConfig()
        self.retrieval.agent = AgentConfig()
        self._validate_config()
        logger.info("Configuration loaded from CODE (no YAML) ")

    def _validate_config(self):
        valid_modes = ["agent", "noagent"]
        if self.triggers.mode not in valid_modes:
            raise ValueError(f"mode must be {valid_modes}")

    def get_dataset_config(self, dataset_name: str) -> DatasetConfig:
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        return self.datasets[dataset_name]

    def get_prompt(self, category: str, prompt_type: str) -> str:
        prompt = self.prompts.get(f"{category}_{prompt_type}")
        return prompt

    def get_prompt_formatted(self, category: str, prompt_type: str, **kwargs) -> str:
        return self.get_prompt(category, prompt_type).format(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "datasets": {name: asdict(cfg) for name, cfg in self.datasets.items()},
            "triggers": asdict(self.triggers),
            "construction": asdict(self.construction),
            "tree_comm": asdict(self.tree_comm),
            "retrieval": asdict(self.retrieval),
            "embeddings": asdict(self.embeddings),
            "nlp": asdict(self.nlp),
            "prompts": self.prompts,
            "output": asdict(self.output),
            "performance": asdict(self.performance),
        }

    def create_output_directories(self):
        for d in [
            self.output.base_dir,
            self.output.graphs_dir,
            self.output.chunks_dir,
            self.output.logs_dir,
        ]:
            os.makedirs(d, exist_ok=True)

    def set_ircot_enabled(self, enabled: bool):
        self.retrieval.agent.enable_ircot = enabled
        logger.info(f"IRCoT {'enabled' if enabled else 'disabled'}")

    def get_ircot_enabled(self) -> bool:
        return self.retrieval.agent.enable_ircot

    def to_dict_ircot(self) -> dict:
        return {
            "enable_ircot": self.retrieval.agent.enable_ircot,
            "max_steps": self.retrieval.agent.max_steps,
        }


_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


def reload_config() -> ConfigManager:
    global _config_instance
    _config_instance = ConfigManager()
    return _config_instance
