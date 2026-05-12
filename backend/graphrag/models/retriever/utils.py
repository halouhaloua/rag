import hashlib
import json
import os
import pickle
from typing import Any, Dict, List, Optional, Set, Union

import numpy as np
import torch
import torch.nn.functional as F


def resolve_device(device: Optional[str] = None) -> torch.device:
    """Unified device resolution logic."""
    if device is not None:
        if device == "cuda" and not torch.cuda.is_available():
            import logging

            logging.getLogger(__name__).warning(
                "Warning: CUDA requested but not available, falling back to CPU"
            )
            return torch.device("cpu")
        return torch.device(device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def resolve_device_str(device: Optional[str] = None) -> str:
    """Unified device resolution returning a plain string (for KTRetriever compat)."""
    if device is not None:
        if device == "cuda":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    return "cuda" if torch.cuda.is_available() else "cpu"


def sanitize_string_field(value: Any) -> str:
    """Normalize a field value (str, list, or other) into a clean string."""
    if not value:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value).strip()


def torch_safe_load(
    filepath: str, map_location: str = "cpu", weights_only: bool = False
) -> Optional[Dict]:
    """Load a torch checkpoint with PyTorch 2.6+ compatibility."""
    try:
        return torch.load(filepath, map_location=map_location, weights_only=weights_only)
    except TypeError:
        return torch.load(filepath, map_location=map_location)
    except Exception as e:
        if "numpy.core.multiarray._reconstruct" in str(e):
            try:
                import importlib

                torch_serialization = importlib.import_module("torch.serialization")
                torch_serialization.add_safe_globals(
                    ["numpy.core.multiarray._reconstruct"]
                )
                return torch.load(filepath, map_location=map_location)
            except Exception:
                raise e
        raise e


def save_embedding_cache(
    cache: Dict[Any, Any],
    filepath: str,
    logger=None,
) -> bool:
    """Unified embedding cache save with torch/numpy fallback."""
    try:
        if not cache:
            return False

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        numpy_cache: Dict[Any, np.ndarray] = {}
        for key, embed in cache.items():
            if embed is None:
                continue
            try:
                if hasattr(embed, "detach"):
                    numpy_cache[key] = embed.detach().cpu().numpy()
                elif isinstance(embed, np.ndarray):
                    numpy_cache[key] = embed
                else:
                    numpy_cache[key] = np.array(embed)
            except Exception:
                continue

        if not numpy_cache:
            return False

        try:
            tensor_cache = {}
            for key, arr in numpy_cache.items():
                if isinstance(arr, np.ndarray):
                    tensor_cache[key] = torch.from_numpy(arr).float()
                else:
                    tensor_cache[key] = arr
            torch.save(tensor_cache, filepath)
        except Exception:
            npz_path = filepath.replace(".pt", ".npz")
            np.savez_compressed(npz_path, **numpy_cache)
            filepath = npz_path

        if logger:
            file_size = os.path.getsize(filepath)
            logger.info(
                f"Saved embedding cache with {len(numpy_cache)} entries to {filepath} (size: {file_size} bytes)"
            )
        return True

    except Exception as e:
        if logger:
            logger.error(f"Error saving embedding cache: {e}")
        return False


def load_embedding_cache(
    filepath: str,
    device: Union[str, torch.device],
    logger=None,
) -> Optional[Dict[Any, torch.Tensor]]:
    """Unified embedding cache loading with npz/torch/pt support."""
    filepath_npz = filepath.replace(".pt", ".npz")

    def _numpy_load(npz_path: str):
        if not os.path.exists(npz_path):
            return None
        try:
            data = np.load(npz_path)
            if len(data.files) == 0:
                data.close()
                return None
            return data
        except Exception as e:
            if logger:
                logger.error(f"Error loading numpy cache: {e}")
            return None

    def _tensor_load(pt_path: str):
        if not os.path.exists(pt_path):
            return None
        try:
            file_size = os.path.getsize(pt_path)
            if file_size < 1000:
                if logger:
                    logger.warning(
                        f"Warning: Cache file too small ({file_size} bytes), likely empty or corrupted"
                    )
                return None
            return torch_safe_load(pt_path, map_location="cpu", weights_only=False)
        except Exception as e:
            if logger:
                logger.error(f"Error loading embedding cache: {e}")
            try:
                os.remove(pt_path)
                if logger:
                    logger.info(f"Removed corrupted cache file: {pt_path}")
            except Exception:
                pass
            return None

    def _items_to_tensors(raw_cache: Dict) -> Dict[Any, torch.Tensor]:
        result: Dict[Any, torch.Tensor] = {}
        for key, embed in raw_cache.items():
            if embed is None:
                continue
            try:
                if isinstance(embed, np.ndarray):
                    emb = torch.from_numpy(embed).float()
                else:
                    emb = embed.cpu() if hasattr(embed, "cpu") else embed
                if isinstance(device, torch.device):
                    target = device
                else:
                    target = torch.device(
                        "cuda"
                        if (device == "cuda" and torch.cuda.is_available())
                        else device
                    )
                if target.type == "cuda" and torch.cuda.is_available():
                    emb = emb.to(target)
                else:
                    emb = emb.to("cpu")
                result[key] = emb
            except Exception as e:
                if logger:
                    logger.warning(
                        f"Warning: Failed to load embedding for {key}: {e}"
                    )
                continue
        return result

    numpy_data = _numpy_load(filepath_npz)
    if numpy_data is not None:
        try:
            raw = {}
            for k in numpy_data.files:
                raw[k] = numpy_data[k]
            numpy_data.close()
            result = _items_to_tensors(raw)
            if logger and result:
                logger.info(
                    f"Loaded embedding cache with {len(result)} entries from {filepath_npz}"
                )
            return result if result else None
        except Exception as e:
            if logger:
                logger.error(f"Error loading embedding cache from {filepath_npz}: {e}")
            return None

    raw_cache = _tensor_load(filepath)
    if raw_cache is None:
        return None
    if not raw_cache:
        if logger:
            logger.warning("Warning: Loaded cache is empty")
        return None

    result = _items_to_tensors(raw_cache)
    if logger and result:
        logger.info(
            f"Loaded embedding cache with {len(result)} entries from {filepath}"
        )
    return result if result else None


def check_cache_consistency(
    current_set: Set,
    cached_set: Set,
    name: str = "cache",
    tolerance: float = 0.1,
    logger=None,
) -> bool:
    """Check if a cache's keys are consistent with the current data."""
    try:
        missing = current_set - cached_set
        if missing:
            if logger:
                logger.info(
                    f"{name} missing {len(missing)} entries from current data"
                )
            return False

        extra = cached_set - current_set
        if len(extra) > len(current_set) * tolerance:
            if logger:
                logger.info(
                    f"{name} has too many extra entries: {len(extra)} extra vs {len(current_set)} current"
                )
            return False

        return True

    except Exception as e:
        if logger:
            logger.error(f"Error checking {name} consistency: {e}")
        return False


def evict_lru_cache(
    cache: Dict, max_size: int, strategy: str = "oldest"
) -> None:
    """Evict entries from a dict cache when it exceeds max_size."""
    if len(cache) <= max_size:
        return
    if strategy == "oldest":
        remove_count = len(cache) - max_size
        oldest = list(cache.keys())[:remove_count]
        for key in oldest:
            del cache[key]
    elif strategy == "recent":
        recent = list(cache.keys())[-max_size:]
        keys_to_remove = [k for k in cache if k not in recent]
        for key in keys_to_remove:
            del cache[key]


def remove_file_safe(filepath: str, logger=None) -> None:
    """Safely remove a file, logging any errors."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        if logger:
            logger.warning(f"Failed to remove {filepath}: {e}")


SCHEMA_SKIP_FIELDS = {
    "name",
    "description",
    "properties",
    "label",
    "chunk id",
    "level",
}


def extract_node_name_and_description(
    node_data: dict,
) -> tuple[str, str]:
    """从节点数据中提取 name 和 description，统一处理新旧数据结构。"""
    if "properties" in node_data and isinstance(node_data["properties"], dict):
        name = sanitize_string_field(node_data["properties"].get("name", ""))
        description = sanitize_string_field(
            node_data["properties"].get("description", "")
        )
    else:
        name = sanitize_string_field(node_data.get("name", ""))
        description = sanitize_string_field(node_data.get("description", ""))
    return name, description


def is_valid_node_text(text: str) -> bool:
    """Check if node text is valid for embedding computation."""
    return bool(
        text and not text.startswith("[Error") and not text.startswith("[Unknown")
    )


def batch_compute_similarities(
    query_embed: torch.Tensor,
    embeddings_list: List[torch.Tensor],
    names: List[str],
) -> Dict[str, float]:
    """批量计算 query 与多个 embeddings 的余弦相似度。"""
    if not embeddings_list:
        return {}
    embeddings_tensor = torch.stack(embeddings_list)
    similarities = F.cosine_similarity(
        query_embed.unsqueeze(0), embeddings_tensor, dim=1
    )
    return {names[i]: max(0.0, similarities[i].item()) for i in range(len(names))}


def check_cache_consistency_simple(
    current_set: Set,
    cache_dict: Dict,
    name: str = "cache",
    logger=None,
) -> bool:
    """Check if a cache dict's keys are consistent with the current data set."""
    return check_cache_consistency(
        current_set, set(cache_dict.keys()), name=name, logger=logger
    )


def safe_remove(filepath: str, logger=None) -> None:
    """Safely remove a file, logging any errors."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        if logger:
            logger.warning(f"Failed to remove {filepath}: {e}")


def save_pickle_cache(
    cache: Dict,
    cache_dir: str,
    dataset: str,
    name: str,
    logger=None,
) -> bool:
    """泛型 pickle 缓存保存。"""
    path = f"{cache_dir}/{dataset}/{name}.pkl"
    try:
        if not cache:
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(cache, f)
        if logger:
            logger.info(f"Saved {name} with {len(cache)} entries to {path}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Error saving {name}: {e}")
        return False


def load_pickle_cache(
    cache_dir: str,
    dataset: str,
    name: str,
    expected_keys: Set = None,
    logger=None,
) -> Optional[Dict]:
    """泛型 pickle 缓存加载。"""
    path = f"{cache_dir}/{dataset}/{name}.pkl"
    if not os.path.exists(path):
        return None
    try:
        size = os.path.getsize(path)
        if size < 1000:
            return None
        with open(path, "rb") as f:
            cache = pickle.load(f)
        if not cache:
            return None
        if expected_keys is not None:
            if not check_cache_consistency(
                expected_keys, set(cache.keys()), name=name, logger=logger
            ):
                return None
        return cache
    except Exception as e:
        if logger:
            logger.error(f"Error loading {name}: {e}")
        safe_remove(path, logger)
        return None


_FAISS_PATH_MAPPING_CACHE: Dict[str, str] = {}


def safe_faiss_path(original_path: str, cache_root: str) -> str:
    """将含非 ASCII 字符的路径转为纯 ASCII 安全路径，FAISS C++ I/O 不支持中文路径。"""
    if not any(ord(c) > 127 for c in original_path):
        return original_path

    safe_name = hashlib.md5(original_path.encode("utf-8")).hexdigest()[:16]
    _, ext = os.path.splitext(original_path)

    safe_dir = os.path.join(cache_root, ".faiss_safe")
    os.makedirs(safe_dir, exist_ok=True)
    safe_path = os.path.join(safe_dir, safe_name + ext)

    _record_faiss_path_mapping(original_path, safe_path, cache_root)
    return safe_path


def faiss_path_exists(original_path: str, cache_root: str) -> bool:
    """检测 FAISS 文件是否存在，自动处理中文路径到安全路径的映射。"""
    if not any(ord(c) > 127 for c in original_path):
        return os.path.exists(original_path)
    safe_path = safe_faiss_path(original_path, cache_root)
    return os.path.exists(safe_path)


def _record_faiss_path_mapping(orig: str, safe: str, cache_root: str):
    """记录中文路径 → 安全路径的映射到 JSON 字典。"""
    mapping_file = os.path.join(cache_root, "faiss_path_mapping.json")
    try:
        mapping = dict(_FAISS_PATH_MAPPING_CACHE)
        if os.path.exists(mapping_file):
            with open(mapping_file, "r", encoding="utf-8") as f:
                stored = json.load(f)
                for k, v in stored.items():
                    mapping.setdefault(k, v)
        mapping[orig] = safe
        os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        _FAISS_PATH_MAPPING_CACHE.clear()
        _FAISS_PATH_MAPPING_CACHE.update(mapping)
    except Exception:
        pass
