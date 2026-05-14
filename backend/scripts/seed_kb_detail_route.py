"""
添加知识库详情页路由并移除旧的表格视图菜单
运行: python scripts/seed_kb_detail_route.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.base_model import generate_nanoid
from app.database import AsyncSessionLocal
from core.menu.model import Menu
from sqlalchemy import select, update


async def seed_kb_detail_route():
    async with AsyncSessionLocal() as db:
        try:
            parent = await db.execute(
                select(Menu).where(
                    Menu.name == "KnowledgeGraph",
                    Menu.is_deleted == False,
                )
            )
            parent_menu = parent.scalar_one_or_none()
            if not parent_menu:
                print("错误: 知识图谱父菜单不存在，请先运行 seed_rag_menus.py")
                return

            # 1. 移除旧的表格视图菜单 (KnowledgeBase → /rag/knowledge-base → /_core/rag/index)
            old_kb = await db.execute(
                select(Menu).where(
                    Menu.name == "KnowledgeBase",
                    Menu.parent_id == parent_menu.id,
                    Menu.is_deleted == False,
                )
            )
            old_kb_menu = old_kb.scalar_one_or_none()
            if old_kb_menu:
                old_kb_menu.is_deleted = True
                print(f"已移除旧菜单: KnowledgeBase → /rag/knowledge-base")

            # 2. 添加详情页隐藏路由 (KnowledgeBaseDetail → /rag/knowledge-base/:kbId)
            existing = await db.execute(
                select(Menu).where(
                    Menu.name == "KnowledgeBaseDetail",
                    Menu.is_deleted == False,
                )
            )
            if existing.scalar_one_or_none():
                print("知识库详情页路由已存在，跳过")
            else:
                detail = Menu(
                    id=generate_nanoid(),
                    parent_id=parent_menu.id,
                    name="KnowledgeBaseDetail",
                    title="menu-title.knowledgeBase",
                    path="/rag/knowledge-base/:kbId",
                    type="menu",
                    component="/_core/rag/detail/index",
                    hideInMenu=True,
                    order=5,
                )
                db.add(detail)
                print("知识库详情页路由添加成功: /rag/knowledge-base/:kbId")

            await db.commit()
            print("\n完成! 变更摘要:")
            print("  - 移除: KnowledgeBase (表格视图) → /rag/knowledge-base")
            print("  + 添加: KnowledgeBaseDetail (详情页) → /rag/knowledge-base/:kbId (隐藏)")
        except Exception as e:
            await db.rollback()
            print(f"失败: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_kb_detail_route())
