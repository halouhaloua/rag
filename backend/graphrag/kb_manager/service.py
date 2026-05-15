from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from graphrag.kb_manager.model import KnowledgeBaseRole


class KnowledgeBasePermissionService:

    @classmethod
    async def get_role_kb_ids(cls, db: AsyncSession, role_id: str) -> List[str]:
        query = select(KnowledgeBaseRole.kb_id).where(
            KnowledgeBaseRole.role_id == role_id,
            KnowledgeBaseRole.is_deleted == False,
        )
        result = await db.execute(query)
        return [row[0] for row in result]

    @classmethod
    async def set_role_kbs(
        cls, db: AsyncSession, role_id: str, kb_ids: List[str]
    ):
        await db.execute(
            delete(KnowledgeBaseRole).where(
                KnowledgeBaseRole.role_id == role_id,
            )
        )
        for kb_id in kb_ids:
            db.add(KnowledgeBaseRole(role_id=role_id, kb_id=kb_id))
        await db.commit()

    @classmethod
    async def check_kb_access(
        cls, db: AsyncSession, kb_id: str, user
    ) -> bool:
        if user.is_superuser:
            return True
        if not user.role_id:
            return False
        query = select(KnowledgeBaseRole.id).where(
            KnowledgeBaseRole.role_id == user.role_id,
            KnowledgeBaseRole.kb_id == kb_id,
            KnowledgeBaseRole.is_deleted == False,
        )
        result = await db.execute(query)
        return result.first() is not None

    @classmethod
    async def get_user_visible_kb_ids(
        cls, db: AsyncSession, user
    ) -> Optional[List[str]]:
        if user.is_superuser:
            return None
        if not user.role_id:
            return []
        return await cls.get_role_kb_ids(db, user.role_id)
