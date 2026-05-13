"""
添加文档管理菜单到 core_menu 表（挂在知识图谱目录下）
运行: python scripts/seed_document_menu.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.base_model import generate_nanoid
from app.database import AsyncSessionLocal
from core.menu.model import Menu
from sqlalchemy import select


async def seed_document_menu():
    async with AsyncSessionLocal() as db:
        try:
            existing = await db.execute(
                select(Menu).where(Menu.name == "DocumentView", Menu.is_deleted == False)
            )
            if existing.scalar_one_or_none():
                print("文档管理菜单已存在，跳过")
                return

            parent = await db.execute(
                select(Menu).where(Menu.name == "KnowledgeGraph", Menu.is_deleted == False)
            )
            parent_menu = parent.scalar_one_or_none()
            if not parent_menu:
                print("错误: 知识图谱父菜单不存在，请先运行 seed_rag_menus.py")
                return

            doc_menu = Menu(
                id=generate_nanoid(),
                parent_id=parent_menu.id,
                name="DocumentView",
                title="menu-title.documentView",
                path="/rag/document",
                type="menu",
                component="/_core/rag/document-view",
                order=0,
            )
            db.add(doc_menu)
            await db.commit()
            print("文档管理菜单添加成功!")
            print("  文档管理 → /rag/document → /_core/rag/document-view")
        except Exception as e:
            await db.rollback()
            print(f"添加失败: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_document_menu())
