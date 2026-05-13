"""
添加知识图谱相关菜单到 core_menu 表
运行: python scripts/seed_rag_menus.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.base_model import generate_nanoid
from app.database import AsyncSessionLocal
from core.menu.model import Menu
from sqlalchemy import select


MENUS = [
    {
        "name": "KnowledgeGraph",
        "title": "menu-title.knowledgeGraph",
        "path": "/rag",
        "type": "catalog",
        "icon": "icon-park-outline:knowledge-base",
        "order": 5,
        "children": [
            {
                "name": "KnowledgeBase",
                "title": "menu-title.knowledgeBase",
                "path": "/rag/knowledge-base",
                "type": "menu",
                "component": "/_core/rag/index",
                "order": 1,
            },
            {
                "name": "GraphVisualization",
                "title": "menu-title.graphVisualization",
                "path": "/rag/graph-view",
                "type": "menu",
                "component": "/_core/rag/graph-view",
                "order": 2,
            },
            {
                "name": "QATest",
                "title": "menu-title.qaTest",
                "path": "/rag/qa",
                "type": "menu",
                "component": "/_core/rag/qa",
                "order": 3,
            },
        ],
    },
]


async def seed_rag_menus():
    async with AsyncSessionLocal() as db:
        try:
            existing = await db.execute(
                select(Menu).where(
                    Menu.name == "KnowledgeGraph",
                    Menu.is_deleted == False,
                )
            )
            if existing.scalar_one_or_none():
                print("知识图谱菜单已存在，跳过")
                return

            for menu_data in MENUS:
                children = menu_data.pop("children", [])
                parent = Menu(
                    id=generate_nanoid(),
                    **menu_data,
                )
                db.add(parent)
                await db.flush()

                for child_data in children:
                    child = Menu(
                        id=generate_nanoid(),
                        parent_id=parent.id,
                        **child_data,
                    )
                    db.add(child)

            await db.commit()
            print("知识图谱菜单添加成功!")
            print("  知识图谱 (catalog)   → /rag")
            print("  ├── 知识库管理        → /rag/knowledge-base")
            print("  ├── 知识图谱可视化     → /rag/graph-view")
            print("  └── 问答测试          → /rag/qa")
        except Exception as e:
            await db.rollback()
            print(f"添加失败: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_rag_menus())
