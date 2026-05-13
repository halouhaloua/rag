"""
自动初始化演示知识库
在应用启动时检测并创建演示知识库，如已存在则跳过。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.base_model import generate_nanoid
from graphrag.rag.model import KnowledgeBase, KnowledgeBaseFile, KnowledgeGraph
from graphrag.rag.service import DEFAULT_SCHEMA
from app.database import AsyncSessionLocal

GRAPHRAG_DIR = Path(__file__).parent.parent / "graphrag"


async def seed_demo_kb():
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.name == "演示知识库",
                    KnowledgeBase.is_deleted == False,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return

            kb = KnowledgeBase(
                id=generate_nanoid(),
                name="演示知识库",
                description="系统内置演示知识库，包含梅西、巴萨等足球领域文档",
                kb_type="demo",
            )
            db.add(kb)
            await db.flush()

            corpus_path = GRAPHRAG_DIR / "data/demo/demo_corpus.json"
            if not corpus_path.exists():
                await db.commit()
                return

            with open(corpus_path, "r", encoding="utf-8") as f:
                docs = json.load(f)

            first_file_id = None
            for i, doc in enumerate(docs):
                title = doc.get("title", f"文档_{i}")
                text = doc.get("text", "")
                content = f"{title}\n{text}"

                file_record = KnowledgeBaseFile(
                    id=generate_nanoid(),
                    kb_id=kb.id,
                    filename=f"{title}.txt",
                    content=content,
                    file_type=".txt",
                    schema_json=DEFAULT_SCHEMA,
                    has_graph=False,
                )
                db.add(file_record)
                await db.flush()

                if i == 0:
                    first_file_id = file_record.id

            if first_file_id:
                graph_path = GRAPHRAG_DIR / "output/graphs/demo_new.json"
                if graph_path.exists():
                    with open(graph_path, "r", encoding="utf-8") as f:
                        graph_data = json.load(f)

                    graph_record = KnowledgeGraph(
                        id=generate_nanoid(),
                        file_id=first_file_id,
                        graph_data=graph_data,
                    )
                    db.add(graph_record)
                    await db.flush()

                    file_obj = await db.get(KnowledgeBaseFile, first_file_id)
                    if file_obj:
                        file_obj.has_graph = True
                        await db.flush()

            await db.commit()
        except Exception as e:
            await db.rollback()
            raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_demo_kb())
    print("演示知识库初始化完成")
