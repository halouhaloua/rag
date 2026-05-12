import os
import json
import glob
import shutil
import re
import asyncio
import pathlib
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from loguru import logger
from graphrag.rag.socket_manager import manager
from graphrag.config import get_config

from graphrag.models.constructor import kt_gen as constructor
from graphrag.models.retriever import (
    agentic_decomposer as decomposer,
    enhanced_kt_retriever as retriever,
)

path = pathlib.Path(__file__).parent.parent

try:
    GRAPHRAG_AVAILABLE = True
    logger.info("GraphRAG components loaded successfully")
except ImportError as e:
    GRAPHRAG_AVAILABLE = False
    logger.error(f"GraphRAG components not available: {e}")

config = None


def get_config_instance():
    global config
    if config is None:
        config = get_config()
    return config


def ensure_demo_schema_exists() -> Path:
    os.makedirs("schemas", exist_ok=True)
    schema_path = path / "schemas/demo.json"
    if not os.path.exists(schema_path):
        demo_schema = {
            "Nodes": [
                "person",
                "location",
                "organization",
                "event",
                "object",
                "concept",
                "time_period",
                "creative_work",
                "biological_entity",
                "natural_phenomenon",
            ],
            "Relations": [
                "is_a",
                "part_of",
                "located_in",
                "created_by",
                "used_by",
                "participates_in",
                "related_to",
                "belongs_to",
                "influences",
                "precedes",
                "arrives_in",
                "comparable_to",
            ],
            "Attributes": [
                "name",
                "date",
                "size",
                "type",
                "description",
                "status",
                "quantity",
                "value",
                "position",
                "duration",
                "time",
            ],
        }
        with open(schema_path, "w") as f:
            json.dump(demo_schema, f, indent=2)
    return schema_path


def get_schema_path_for_dataset(dataset_name: str) -> Path:
    if dataset_name and dataset_name != "demo":
        ds_schema = path / f"schemas/{dataset_name}.json"
        if os.path.exists(ds_schema):
            return ds_schema
    return ensure_demo_schema_exists()


async def send_progress_update(client_id: str, stage: str, progress: int, message: str):
    await manager.send_message(
        {
            "type": "progress",
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        },
        client_id,
    )


async def clear_cache_files(dataset_name: str):
    try:
        faiss_cache_dir = path / f"retriever/faiss_cache_new/{dataset_name}"
        if os.path.exists(faiss_cache_dir):
            shutil.rmtree(faiss_cache_dir)
        chunk_file = path / f"output/chunks/{dataset_name}.txt"
        if os.path.exists(chunk_file):
            os.remove(chunk_file)
        graph_file = path / f"output/graphs/{dataset_name}_new.json"
        if os.path.exists(graph_file):
            os.remove(graph_file)
        for pattern in [
            path / f"output/logs/{dataset_name}_*.log",
            path / f"output/chunks/{dataset_name}_*",
            path / f"output/graphs/{dataset_name}_*",
        ]:
            for fp in glob.glob(str(pattern)):
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                    elif os.path.isdir(fp):
                        shutil.rmtree(fp)
                except Exception as e:
                    logger.warning(f"Failed to clear {fp}: {e}")
        logger.info(f"Cache cleanup completed for dataset: {dataset_name}")
    except Exception as e:
        logger.error(f"Error clearing cache files for {dataset_name}: {e}")


async def extract_text_from_document(file_path: str, file_ext: str) -> str:
    try:
        if file_ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif file_ext == ".pdf":
            try:
                import PyPDF2

                text = ""
                with open(file_path, "rb") as f:
                    for page in PyPDF2.PdfReader(f).pages:
                        text += page.extract_text() + "\n"
                return text
            except ImportError:
                try:
                    import pdfplumber

                    text = ""
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            text += page.extract_text() + "\n"
                    return text
                except ImportError:
                    return f"[PDF content from {os.path.basename(file_path)}]"
        elif file_ext in [".doc", ".docx"]:
            try:
                import docx

                return "\n".join(p.text for p in docx.Document(file_path).paragraphs)
            except ImportError:
                return f"[Word content from {os.path.basename(file_path)}]"
    except Exception as e:
        return (
            f"[Error extracting content from {os.path.basename(file_path)}: {str(e)}]"
        )
    return ""


async def extract_text_from_spreadsheet(file_path: str, file_ext: str):
    try:
        if file_ext == ".csv":
            import csv

            text = ""
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for row in csv.reader(f):
                    text += ", ".join(row) + "\n"
            return text
        elif file_ext in [".xls", ".xlsx"]:
            try:
                import pandas as pd

                return pd.read_excel(file_path).to_string(index=False)
            except ImportError:
                import openpyxl

                wb = openpyxl.load_workbook(file_path)
                text = ""
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    text += f"Sheet: {sheet}\n"
                    for row in ws.iter_rows():
                        text += (
                            ", ".join(str(c.value) if c.value else "" for c in row)
                            + "\n"
                        )
                    text += "\n"
                return text
    except Exception as e:
        return f"[Error: {str(e)}]"
    return ""


async def process_upload_files(files: List, client_id: str) -> tuple:
    if not files:
        raise Exception("No files provided")
    dataset_name = f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    upload_dir = path / f"data/uploaded/{dataset_name}"
    os.makedirs(upload_dir, exist_ok=True)
    await send_progress_update(client_id, "upload", 10, f"创建数据集: {dataset_name}")
    contents = []
    for i, file in enumerate(files):
        progress = 10 + int((i + 1) / len(files) * 70)
        await send_progress_update(
            client_id, "upload", progress, f"处理文件: {file.filename}"
        )
        file_path = os.path.join(upload_dir, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext in [".csv", ".xls", ".xlsx"]:
            text = await extract_text_from_spreadsheet(file_path, file_ext)
        else:
            text = await extract_text_from_document(file_path, file_ext)
        contents.append({"filename": file.filename, "content": text})
    corpus_path = (
        upload_dir / "corpus.json"
        if hasattr(upload_dir, "parent")
        else Path(os.path.join(upload_dir, "corpus.json"))
    )
    corpus_path = Path(os.path.join(upload_dir, "corpus.json"))
    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(contents, f, ensure_ascii=False, indent=2)
    await send_progress_update(client_id, "upload", 100, "文件上传完成!")
    return dataset_name, len(files)


async def construct_graph_service(dataset_name: str, client_id: str):
    if not GRAPHRAG_AVAILABLE:
        raise Exception("GraphRAG components not available.")
    await send_progress_update(client_id, "construction", 2, "清理旧缓存文件...")
    await clear_cache_files(dataset_name)
    await send_progress_update(client_id, "construction", 5, "初始化图构建器...")
    corpus_path = path / f"data/uploaded/{dataset_name}/corpus.json"
    schema_path = get_schema_path_for_dataset(dataset_name)
    if not os.path.exists(corpus_path):
        corpus_path = path / "data/demo/demo_corpus.json"
    if not os.path.exists(corpus_path):
        raise Exception("Dataset not found")
    await send_progress_update(client_id, "construction", 10, "加载配置和语料库...")
    cfg = get_config_instance()
    builder = constructor.KTBuilder(
        dataset_name, schema_path, mode=cfg.construction.mode, config=cfg
    )
    await send_progress_update(client_id, "construction", 20, "开始实体关系抽取...")

    def build_graph_sync():
        return builder.build_knowledge_graph(corpus_path)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, build_graph_sync)
    await send_progress_update(client_id, "construction", 95, "准备可视化数据...")
    graph_path = path / f"output/graphs/{dataset_name}_new.json"
    graph_vis_data = await prepare_graph_visualization(str(graph_path))
    await send_progress_update(client_id, "construction", 100, "图构建完成!")
    try:
        await manager.send_message(
            {
                "type": "complete",
                "stage": "construction",
                "message": "图构建完成!",
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )
    except Exception as _e:
        logger.warning(f"Failed to send completion message: {_e}")
    return graph_vis_data


def prepare_subquery_visualization(
    sub_questions: List[Dict], reasoning_steps: List[Dict]
) -> Dict:
    subquery_nodes = []
    subquery_links = []
    for idx, sq in enumerate(sub_questions):
        q_text = sq.get("sub-question", f"子问题 {idx + 1}")
        nid = f"sq_{idx}"
        subquery_nodes.append(
            {
                "id": nid,
                "name": q_text[:30],
                "category": "sub_question",
                "symbolSize": 20,
            }
        )
        step_data = reasoning_steps[idx] if idx < len(reasoning_steps) else {}
        triples = step_data.get("triples", [])[:5]
        for t_idx, triple in enumerate(triples):
            tid = f"triple_{idx}_{t_idx}"
            parts = (
                [p.strip().strip("'[]") for p in triple.split(",")]
                if "," in triple
                else [triple]
            )
            if len(parts) >= 3:
                subquery_nodes.append(
                    {
                        "id": tid,
                        "name": parts[1][:20],
                        "category": "triple",
                        "symbolSize": 10,
                    }
                )
                subquery_links.append(
                    {"source": nid, "target": tid, "name": parts[0][:15], "value": 1}
                )
    return {"nodes": subquery_nodes, "links": subquery_links}


def prepare_retrieved_graph_visualization(triples: List[str]) -> Dict:
    nodes = {}
    links = []
    for triple in triples:
        parts = (
            [p.strip().strip("'[]") for p in triple.split(",")]
            if "," in triple
            else [triple, "", ""]
        )
        if len(parts) >= 3:
            h, r, t = parts[0], parts[1], parts[2]
            if h and h not in nodes:
                nodes[h] = {
                    "id": h,
                    "name": h[:20],
                    "category": "entity",
                    "symbolSize": 15,
                }
            if t and t not in nodes:
                nodes[t] = {
                    "id": t,
                    "name": t[:20],
                    "category": "entity",
                    "symbolSize": 15,
                }
            links.append({"source": h, "target": t, "name": r[:15], "value": 1})
    return {
        "nodes": list(nodes.values()),
        "links": links,
        "categories": [{"name": "entity"}],
        "stats": {"total_nodes": len(nodes), "total_edges": len(links)},
    }


def prepare_reasoning_flow_visualization(reasoning_steps: List[Dict]) -> Dict:
    nodes = [
        {"id": "question", "name": "问题", "category": "question", "symbolSize": 25}
    ]
    links = []
    for i, step in enumerate(reasoning_steps):
        sid = f"step_{i}"
        label = step.get("question", f"步骤 {i + 1}")[:20]
        nodes.append(
            {
                "id": sid,
                "name": label,
                "category": step.get("type", "step"),
                "symbolSize": 20,
            }
        )
        links.append(
            {
                "source": "question" if i == 0 else f"step_{i - 1}",
                "target": sid,
                "name": "→",
                "value": 1,
            }
        )
    return {
        "nodes": nodes,
        "links": links,
        "categories": [
            {"name": "question"},
            {"name": "sub_question"},
            {"name": "ircot_step"},
        ],
    }


# ──────────────────────────────────────────────
# Non‑streaming ask (kept for /chat/message/chat)
# ──────────────────────────────────────────────
async def ask_question_service(dataset_name: str, question: str, client_id: str):
    if not GRAPHRAG_AVAILABLE:
        raise Exception("GraphRAG components not available.")

    graph_path = path / f"output/graphs/{dataset_name}_new.json"
    schema_path = get_schema_path_for_dataset(dataset_name)
    if not os.path.exists(graph_path):
        graph_path = path / "output/graphs/demo_new.json"
    if not os.path.exists(graph_path):
        raise Exception("Graph not found. Please construct graph first.")

    cfg = get_config_instance()
    graphq = decomposer.GraphQ(dataset_name, config=None)
    kt_retriever = retriever.KTRetriever(
        dataset_name,
        str(graph_path),
        recall_paths=cfg.retrieval.recall_paths,
        schema_path=str(schema_path),
        top_k=cfg.retrieval.top_k_filter,
        mode="agent",
        config=cfg,
    )

    kt_retriever.build_indices()

    def _dedup(items):
        return list({x: None for x in items}.keys())

    def _merge_chunk_contents(ids, mapping):
        return [mapping.get(i, f"[Missing content for chunk {i}]") for i in ids]

    await send_progress_update(client_id, "retrieval", 50, "问题分解...")
    try:
        decomposition = graphq.decompose(question, str(schema_path))
        sub_questions = decomposition.get("sub_questions", [])
        involved_types = decomposition.get("involved_types", {})
    except Exception as e:
        logger.error(f"Decompose failed: {e}")
        sub_questions = [{"sub-question": question}]
        involved_types = {"nodes": [], "relations": [], "attributes": []}

    reasoning_steps = []
    all_triples = set()
    all_chunk_ids = set()
    all_chunk_contents: Dict[str, str] = {}

    await send_progress_update(client_id, "retrieval", 65, "初始检索...")
    for idx, sq in enumerate(sub_questions):
        sq_text = sq.get("sub-question", question)
        retrieval_results, elapsed = kt_retriever.process_retrieval_results(
            sq_text, top_k=cfg.retrieval.top_k_filter, involved_types=involved_types
        )
        triples = retrieval_results.get("triples", []) or []
        chunk_ids = retrieval_results.get("chunk_ids", []) or []
        chunk_contents = retrieval_results.get("chunk_contents", []) or []
        if isinstance(chunk_contents, dict):
            for cid, ctext in chunk_contents.items():
                all_chunk_contents[cid] = ctext
        else:
            for i_c, cid in enumerate(chunk_ids):
                if i_c < len(chunk_contents):
                    all_chunk_contents[cid] = chunk_contents[i_c]
        all_triples.update(triples)
        all_chunk_ids.update(chunk_ids)
        reasoning_steps.append(
            {
                "type": "sub_question",
                "question": sq_text,
                "triples": triples[:10],
                "triples_count": len(triples),
                "chunks_count": len(chunk_ids),
                "processing_time": elapsed,
                "chunk_contents": list(all_chunk_contents.values())[:3],
            }
        )

    initial_triples = _dedup(list(all_triples))
    initial_chunk_ids = list(set(all_chunk_ids))
    initial_chunk_contents = _merge_chunk_contents(
        initial_chunk_ids, all_chunk_contents
    )
    context_initial = (
        "=== Triples ===\n"
        + "\n".join(initial_triples[:20])
        + "\n=== Chunks ===\n"
        + "\n".join(initial_chunk_contents[:10])
    )
    init_prompt = kt_retriever.generate_prompt(question, context_initial)
    try:
        initial_answer = kt_retriever.generate_answer(init_prompt)
    except Exception as e:
        initial_answer = f"Initial answer failed: {e}"
    final_answer = initial_answer

    if not cfg.retrieval.agent.enable_ircot:
        final_triples = initial_triples[:20]
        final_chunk_contents = initial_chunk_contents
        visualization_data = {
            "subqueries": prepare_subquery_visualization(
                sub_questions, reasoning_steps
            ),
            "knowledge_graph": prepare_retrieved_graph_visualization(final_triples),
            "reasoning_flow": prepare_reasoning_flow_visualization(reasoning_steps),
            "retrieval_details": {
                "total_triples": len(final_triples),
                "total_chunks": len(final_chunk_contents),
                "sub_questions_count": len(sub_questions),
                "triples_by_subquery": [
                    r.get("triples_count", 0)
                    for r in reasoning_steps
                    if r.get("type") == "sub_question"
                ],
            },
        }
        return {
            "answer": final_answer,
            "sub_questions": sub_questions,
            "retrieved_triples": final_triples,
            "retrieved_chunks": final_chunk_contents[:10],
            "reasoning_steps": reasoning_steps,
            "visualization_data": visualization_data,
        }

    # IRCoT iterative refinement
    thoughts = [f"Initial: {final_answer[:200]}"]
    current_query = question

    max_steps = getattr(getattr(cfg.retrieval, "agent", object()), "max_steps", 3)
    for step in range(1, max_steps + 1):
        loop_triples = _dedup(list(all_triples))
        loop_chunk_ids = list(set(all_chunk_ids))
        loop_chunk_contents = _merge_chunk_contents(loop_chunk_ids, all_chunk_contents)
        loop_ctx = (
            "=== Triples ===\n"
            + "\n".join(loop_triples[:20])
            + "\n=== Chunks ===\n"
            + "\n".join(loop_chunk_contents[:10])
        )
        loop_prompt = f"""
        You are an expert knowledge assistant using iterative retrieval with chain-of-thought reasoning.
        Current Question: {question}
        Current Iteration Query: {current_query}
        Knowledge Context:\n{loop_ctx}
        Previous Thoughts: {" | ".join(thoughts) if thoughts else "None"}
        Instructions:
        1. If enough info answer with: So the answer is: <answer>
        2. Else propose new query with: The new query is: <query>
        Your reasoning:
        """
        try:
            reasoning = kt_retriever.generate_answer(loop_prompt)
        except Exception as e:
            reasoning = f"Reasoning error: {e}"
        thoughts.append(reasoning[:400])
        reasoning_steps.append(
            {
                "type": "ircot_step",
                "question": current_query,
                "triples": loop_triples[:10],
                "triples_count": len(loop_triples),
                "chunks_count": len(loop_chunk_ids),
                "processing_time": 0,
                "chunk_contents": loop_chunk_contents[:3],
                "thought": reasoning[:300],
            }
        )
        if "So the answer is:" in reasoning:
            m = re.search(
                r"So the answer is:\s*(.*)", reasoning, flags=re.IGNORECASE | re.DOTALL
            )
            final_answer = m.group(1).strip() if m else reasoning
            break
        if "The new query is:" not in reasoning:
            final_answer = initial_answer or reasoning
            break
        new_query = reasoning.split("The new query is:", 1)[1].strip().splitlines()[0]
        if not new_query or new_query == current_query:
            final_answer = initial_answer or reasoning
            break
        current_query = new_query

        try:
            new_ret, _ = kt_retriever.process_retrieval_results(
                current_query, top_k=cfg.retrieval.top_k_filter
            )
            new_triples = new_ret.get("triples", []) or []
            new_chunk_ids = new_ret.get("chunk_ids", []) or []
            new_cc = new_ret.get("chunk_contents", []) or []
            if isinstance(new_cc, dict):
                for cid, ct in new_cc.items():
                    all_chunk_contents[cid] = ct
            else:
                for i_c, cid in enumerate(new_chunk_ids):
                    if i_c < len(new_cc):
                        all_chunk_contents[cid] = new_cc[i_c]
            all_triples.update(new_triples)
            all_chunk_ids.update(new_chunk_ids)
        except Exception as e:
            logger.error(f"Iterative retrieval failed: {e}")
            break

    final_triples = _dedup(list(all_triples))[:20]
    final_chunk_ids = list(set(all_chunk_ids))
    final_chunk_contents = _merge_chunk_contents(final_chunk_ids, all_chunk_contents)[:10]
    visualization_data = {
        "subqueries": prepare_subquery_visualization(sub_questions, reasoning_steps),
        "knowledge_graph": prepare_retrieved_graph_visualization(final_triples),
        "reasoning_flow": prepare_reasoning_flow_visualization(reasoning_steps),
        "retrieval_details": {
            "total_triples": len(final_triples),
            "total_chunks": len(final_chunk_contents),
            "sub_questions_count": len(sub_questions),
            "triples_by_subquery": [
                r.get("triples_count", 0)
                for r in reasoning_steps
                if r.get("type") == "sub_question"
            ],
        },
    }
    return {
        "answer": final_answer,
        "sub_questions": sub_questions,
        "retrieved_triples": final_triples,
        "retrieved_chunks": final_chunk_contents,
        "reasoning_steps": reasoning_steps,
        "visualization_data": visualization_data,
    }


def _sse(**kwargs):
    return f"data: {json.dumps(kwargs, ensure_ascii=False)}\n\n"


async def ask_question_service_stream(dataset_name: str, question: str, client_id: str):
    if not GRAPHRAG_AVAILABLE:
        yield _sse(type="error", message="GraphRAG components not available.")
        return

    yield _sse(type="status", progress=10, message="初始化检索系统 ...")

    graph_path = path / f"output/graphs/{dataset_name}_new.json"
    schema_path = get_schema_path_for_dataset(dataset_name)
    if not os.path.exists(graph_path):
        graph_path = path / "output/graphs/demo_new.json"
    if not os.path.exists(graph_path):
        yield _sse(type="error", message="Graph not found.")
        return

    cfg = get_config_instance()
    graphq = decomposer.GraphQ(dataset_name, config=None)
    kt_retriever = retriever.KTRetriever(
        dataset_name,
        str(graph_path),
        recall_paths=cfg.retrieval.recall_paths,
        schema_path=str(schema_path),
        top_k=cfg.retrieval.top_k_filter,
        mode="agent",
        config=cfg,
    )

    yield _sse(type="status", progress=40, message="构建索引...")
    kt_retriever.build_indices()

    def _dedup(items):
        return list({x: None for x in items}.keys())

    def _merge_chunk_contents(ids, mapping):
        return [mapping.get(i, f"[Missing content for chunk {i}]") for i in ids]

    yield _sse(type="status", progress=50, message="问题分解...")
    try:
        decomposition = graphq.decompose(question, str(schema_path))
        sub_questions = decomposition.get("sub_questions", [])
        involved_types = decomposition.get("involved_types", {})
    except Exception as e:
        logger.error(f"Decompose failed: {e}")
        sub_questions = [{"sub-question": question}]
        involved_types = {"nodes": [], "relations": [], "attributes": []}

    reasoning_steps = []
    all_triples = set()
    all_chunk_ids = set()
    all_chunk_contents: Dict[str, str] = {}

    yield _sse(type="status", progress=65, message="初始检索...")
    for _, sq in enumerate(sub_questions):
        sq_text = sq.get("sub-question", question)
        retrieval_results, elapsed = kt_retriever.process_retrieval_results(
            sq_text, top_k=cfg.retrieval.top_k_filter, involved_types=involved_types
        )
        triples = retrieval_results.get("triples", []) or []
        chunk_ids = retrieval_results.get("chunk_ids", []) or []
        chunk_contents = retrieval_results.get("chunk_contents", []) or []
        if isinstance(chunk_contents, dict):
            for cid, ctext in chunk_contents.items():
                all_chunk_contents[cid] = ctext
        else:
            for i_c, cid in enumerate(chunk_ids):
                if i_c < len(chunk_contents):
                    all_chunk_contents[cid] = chunk_contents[i_c]
        all_triples.update(triples)
        all_chunk_ids.update(chunk_ids)
        reasoning_steps.append(
            {
                "type": "sub_question",
                "question": sq_text,
                "triples": triples[:10],
                "triples_count": len(triples),
                "chunks_count": len(chunk_ids),
                "processing_time": elapsed,
                "chunk_contents": list(all_chunk_contents.values())[:3],
            }
        )

    yield _sse(
        type="metadata",
        sub_questions=sub_questions,
        triples=list(all_triples)[:20],
        chunks=list(all_chunk_contents.values())[:10],
    )

    initial_triples = _dedup(list(all_triples))
    initial_chunk_ids = list(set(all_chunk_ids))
    initial_chunk_contents = _merge_chunk_contents(
        initial_chunk_ids, all_chunk_contents
    )
    context_initial = (
        "=== Triples ===\n"
        + "\n".join(initial_triples[:20])
        + "\n=== Chunks ===\n"
        + "\n".join(initial_chunk_contents[:10])
    )
    init_prompt = kt_retriever.generate_prompt(question=question,
                                               sub_question=sub_questions, 
                                               context=context_initial)

    # ── Non-IRCoT path ──
    if not cfg.retrieval.agent.enable_ircot:
        yield _sse(type="answer_start")
        answer_tokens = []
        try:
            async for token in kt_retriever.generate_answer_stream(init_prompt):
                answer_tokens.append(token)
                yield _sse(type="token", phase="answer", text=token)
        except Exception as e:
            err = f"答案生成失败: {e}"
            answer_tokens.append(err)
            yield _sse(type="token", phase="answer", text=err)
        yield _sse(type="answer_end")
        final_triples = initial_triples[:20]
        think = {
            "type": "init",
            "question": question,
            "triples": initial_triples,
            "triples_count": len(initial_triples),
            "chunks_count": len(initial_chunk_ids),
            "processing_time": elapsed,
            "chunk_contents": initial_chunk_contents[:3],
            "thought": "".join(answer_tokens)
        }
        reasoning_steps.append(think)

        visualization_data = {
            "subqueries": prepare_subquery_visualization(
                sub_questions, reasoning_steps
            ),
            "knowledge_graph": prepare_retrieved_graph_visualization(final_triples),
            "reasoning_flow": prepare_reasoning_flow_visualization(reasoning_steps),
            "retrieval_details": {
                "total_triples": len(final_triples),
                "total_chunks": len(initial_chunk_contents),
                "sub_questions_count": len(sub_questions),
                "triples_by_subquery": [
                    r.get("triples_count", 0)
                    for r in reasoning_steps
                    if r.get("type") == "sub_question"
                ],
            },
        }
        yield _sse(type="reasoning_steps", data={"reasoning_steps": reasoning_steps})   
        yield _sse(type="visualization", data=visualization_data)
        yield _sse(type="done", answer="".join(answer_tokens))
        return

    # ── IRCoT path ──
    yield _sse(type="reasoning_start", step=0)
    initial_answer_tokens = []
    try:
        async for token in kt_retriever.generate_answer_stream(init_prompt):
            initial_answer_tokens.append(token)
            yield _sse(type="token", phase="reasoning", text=token)
    except Exception as e:
        err = f"初始答案生成失败: {e}"
        initial_answer_tokens.append(err)
        yield _sse(type="token", phase="reasoning", text=err)
    initial_answer = "".join(initial_answer_tokens)
    think = {
        "type": "init",
        "question": question,
        "triples": initial_triples,
        "triples_count": len(initial_triples),
        "chunks_count": len(initial_chunk_ids),
        "processing_time": elapsed,
        "chunk_contents": initial_chunk_contents[:3],
        "thought": initial_answer
    }
    reasoning_steps.append(think)
    yield _sse(type="reasoning_steps", data={"reasoning_steps": reasoning_steps})
    yield _sse(
        type="reasoning_end",
        step=0,
        thought=initial_answer[:300],
        query=question,
        triples=list(all_triples)[:5],
        triples_count=len(all_triples),
        chunks_count=len(all_chunk_contents),
    )

    thoughts = [f"Initial: {initial_answer[:200]}"]
    current_query = question
    yield _sse(type="ircot_start")
    max_steps = getattr(getattr(cfg.retrieval, "agent", object()), "max_steps", 3)
    final_answer = None

    for step in range(1, max_steps + 1):
        loop_triples = _dedup(list(all_triples))
        loop_chunk_ids = list(set(all_chunk_ids))
        loop_chunk_contents = _merge_chunk_contents(loop_chunk_ids, all_chunk_contents)
        loop_ctx = (
            "=== Triples ===\n"
            + "\n".join(loop_triples[:20])
            + "\n=== Chunks ===\n"
            + "\n".join(loop_chunk_contents[:10])
        )
        loop_prompt = f"""
        You are an expert knowledge assistant using iterative retrieval with chain-of-thought reasoning.
        Current Question: {question}
        Current Iteration Query: {current_query}
        Knowledge Context:\n{loop_ctx}
        Previous Thoughts: {" | ".join(thoughts) if thoughts else "None"}
        Instructions:
        1. If enough info answer with: So the answer is: <answer>
        2. Else propose new query with: The new query is: <query>
        Your reasoning:
        """
        yield _sse(type="reasoning_start", step=step)
        reasoning_tokens = []
        try:
            async for token in kt_retriever.generate_answer_stream(loop_prompt):
                reasoning_tokens.append(token)
                yield _sse(type="token", phase="reasoning", text=token)
        except Exception as e:
            err = f"推理错误: {e}"
            reasoning_tokens.append(err)
            yield _sse(type="token", phase="reasoning", text=err)
        reasoning = "".join(reasoning_tokens)
        thoughts.append(reasoning[:400])
        reasoning_steps.append(
            {
                "type": "ircot_step",
                "question": current_query,
                "triples": loop_triples[:10],
                "triples_count": len(loop_triples),
                "chunks_count": len(loop_chunk_ids),
                "processing_time": 0,
                "chunk_contents": loop_chunk_contents[:3],
                "thought": reasoning[:300],
            }
        )
        yield _sse(
            type="reasoning_end",
            step=step,
            thought=reasoning[:300],
            query=current_query,
            triples=loop_triples[:5],
            triples_count=len(loop_triples),
            chunks_count=len(loop_chunk_ids),
        )
        if "So the answer is:" in reasoning:
            m = re.search(
                r"So the answer is:\s*(.*)", reasoning, flags=re.IGNORECASE | re.DOTALL
            )
            final_answer = m.group(1).strip() if m else reasoning
            yield _sse(type="answer_found", answer=final_answer)
            break
        if "The new query is:" not in reasoning:
            final_answer = initial_answer or reasoning
            break
        new_query = reasoning.split("The new query is:", 1)[1].strip().splitlines()[0]
        if not new_query or new_query == current_query:
            final_answer = initial_answer or reasoning
            break
        current_query = new_query
        yield _sse(
            type="status",
            progress=min(90, 75 + step * 5),
            message=f"迭代检索 Step {step}...",
        )
        try:
            new_ret, _ = kt_retriever.process_retrieval_results(
                current_query, top_k=cfg.retrieval.top_k_filter
            )
            new_triples = new_ret.get("triples", []) or []
            new_chunk_ids = new_ret.get("chunk_ids", []) or []
            new_cc = new_ret.get("chunk_contents", []) or []
            if isinstance(new_cc, dict):
                for cid, ct in new_cc.items():
                    all_chunk_contents[cid] = ct
            else:
                for i_c, cid in enumerate(new_chunk_ids):
                    if i_c < len(new_cc):
                        all_chunk_contents[cid] = new_cc[i_c]
            all_triples.update(new_triples)
            all_chunk_ids.update(new_chunk_ids)
        except Exception as e:
            logger.error(f"Iterative retrieval failed: {e}")
            break

    yield _sse(type="ircot_end")
    if final_answer is None:
        final_answer = initial_answer
    final_triples = _dedup(list(all_triples))[:20]
    final_chunk_ids = list(set(all_chunk_ids))
    final_chunk_contents = _merge_chunk_contents(final_chunk_ids, all_chunk_contents)[:10]
    visualization_data = {
        "subqueries": prepare_subquery_visualization(sub_questions, reasoning_steps),
        "knowledge_graph": prepare_retrieved_graph_visualization(final_triples),
        "reasoning_flow": prepare_reasoning_flow_visualization(reasoning_steps),
        "retrieval_details": {
            "total_triples": len(final_triples),
            "total_chunks": len(final_chunk_contents),
            "sub_questions_count": len(sub_questions),
            "triples_by_subquery": [
                r.get("triples_count", 0)
                for r in reasoning_steps
                if r.get("type") == "sub_question"
            ],
        },
    }
    yield _sse(type="reasoning_steps", data={"reasoning_steps": reasoning_steps})
    yield _sse(type="visualization", data=visualization_data)
    yield _sse(type="done", answer=final_answer)


async def get_datasets_service():
    datasets = []
    upload_dir = path / "data/uploaded"
    if os.path.exists(upload_dir):
        for item in os.listdir(upload_dir):
            item_path = os.path.join(upload_dir, item)
            if os.path.isdir(item_path):
                corpus_path = os.path.join(item_path, "corpus.json")
                if os.path.exists(corpus_path):
                    graph_path = path / f"output/graphs/{item}_new.json"
                    status = (
                        "ready" if os.path.exists(graph_path) else "needs_construction"
                    )
                    has_custom_schema = os.path.exists(path / f"schemas/{item}.json")
                    datasets.append(
                        {
                            "name": item,
                            "type": "uploaded",
                            "status": status,
                            "has_custom_schema": has_custom_schema,
                        }
                    )
    demo_corpus = path / "data/demo/demo_corpus.json"
    if os.path.exists(demo_corpus):
        demo_graph = path / "output/graphs/demo_new.json"
        datasets.append(
            {
                "name": "demo",
                "type": "demo",
                "status": "ready"
                if os.path.exists(demo_graph)
                else "needs_construction",
                "has_custom_schema": False,
            }
        )
    return {"datasets": datasets}


async def upload_schema_service(dataset_name: str, schema_file):
    content = await schema_file.read()
    schema_path = path / f"schemas/{dataset_name}.json"
    with open(schema_path, "wb") as f:
        f.write(content)
    return {"message": f"Schema uploaded successfully for dataset '{dataset_name}'"}


async def delete_dataset_service(dataset_name: str):
    upload_dir = path / f"data/uploaded/{dataset_name}"
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
    graph_path = path / f"output/graphs/{dataset_name}_new.json"
    if os.path.exists(graph_path):
        os.remove(graph_path)
    schema_path = path / f"schemas/{dataset_name}.json"
    if os.path.exists(schema_path):
        os.remove(schema_path)
    return {"message": f"Dataset '{dataset_name}' deleted"}


async def reconstruct_dataset_service(dataset_name: str, client_id: str):
    return await construct_graph_service(dataset_name, client_id)


def convert_graphrag_format(graph_data: list) -> Dict:
    nodes_dict = {}
    links = []
    for item in graph_data:
        if not isinstance(item, dict):
            continue
        start_node = item.get("start_node", {})
        end_node = item.get("end_node", {})
        relation = item.get("relation", "related_to")
        if start_node:
            sid = start_node.get("properties", {}).get("name", "")
            if sid and sid not in nodes_dict:
                nodes_dict[sid] = {
                    "id": sid,
                    "name": sid[:30],
                    "category": start_node.get("properties", {}).get(
                        "schema_type", start_node.get("label", "entity")
                    ),
                    "symbolSize": 25,
                    "properties": start_node.get("properties", {}),
                }
        if end_node:
            eid = end_node.get("properties", {}).get("name", "")
            if isinstance(eid, (list, dict)):
                eid = str(eid.get("name", "")) if isinstance(eid, dict) else str(eid)
            if eid and eid not in nodes_dict:
                nodes_dict[eid] = {
                    "id": eid,
                    "name": eid[:30],
                    "category": end_node.get("properties", {}).get(
                        "schema_type", end_node.get("label", "entity")
                    ),
                    "symbolSize": 25,
                    "properties": end_node.get("properties", {}),
                }
        if sid and eid:
            links.append({"source": sid, "target": eid, "name": relation, "value": 1})
    categories = list(set(n["category"] for n in nodes_dict.values() if n["category"]))
    return {
        "nodes": list(nodes_dict.values()),
        "links": links,
        "categories": [{"name": c} for c in categories],
        "stats": {
            "total_nodes": len(nodes_dict),
            "total_edges": len(links),
            "displayed_nodes": len(nodes_dict),
            "displayed_edges": len(links),
        },
    }


def convert_standard_format(graph_data: Dict) -> Dict:
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", []) or graph_data.get("links", [])
    categories = graph_data.get("categories", [])
    for n in nodes:
        if "symbolSize" not in n:
            n["symbolSize"] = 25
    for e in edges:
        if "value" not in e:
            e["value"] = 1
    return {
        "nodes": nodes,
        "links": edges,
        "categories": categories,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "displayed_nodes": len(nodes),
            "displayed_edges": len(edges),
        },
    }


async def prepare_graph_visualization(graph_path: str) -> Dict:
    if os.path.exists(graph_path):
        with open(graph_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    else:
        return {"nodes": [], "links": [], "categories": [], "stats": {}}
    if isinstance(graph_data, list):
        return convert_graphrag_format(graph_data)
    elif isinstance(graph_data, dict) and "nodes" in graph_data:
        return convert_standard_format(graph_data)
    return {"nodes": [], "links": [], "categories": [], "stats": {}}


async def get_graph_data_service(dataset_name: str):
    graph_path = path / f"output/graphs/{dataset_name}_new.json"
    return await prepare_graph_visualization(str(graph_path))
