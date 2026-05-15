from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_service import BaseService
from pydantic import BaseModel as PydanticBaseModel

from graphrag.rag.model import KnowledgeBase, KnowledgeBaseFile, KnowledgeGraph
from graphrag.rag.schema import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseFileCreate, KnowledgeGraphCreate


class KnowledgeBaseService(
    BaseService[KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate]
):
    model = KnowledgeBase

    @classmethod
    async def get_list_with_file_count(
        cls, db: AsyncSession, page: int = 1, page_size: int = 200, name: str = None
    ):
        from sqlalchemy import func as sa_func

        filters = []
        if name:
            filters.append(cls.model.name.ilike(f"%{name}%"))
        items, total = await cls.get_list(db, page=page, page_size=page_size, filters=filters)
        for item in items:
            item.file_count = 0
        if items:
            from sqlalchemy import func as sa_func

            kb_ids = [item.id for item in items]
            count_query = (
                select(
                    KnowledgeBaseFile.kb_id,
                    sa_func.count(KnowledgeBaseFile.id).label("cnt"),
                )
                .where(
                    KnowledgeBaseFile.kb_id.in_(kb_ids),
                    KnowledgeBaseFile.is_deleted == False,
                )
                .group_by(KnowledgeBaseFile.kb_id)
            )
            result = await db.execute(count_query)
            count_map = {row.kb_id: row.cnt for row in result}
            for item in items:
                item.file_count = count_map.get(item.id, 0)
        return items, total


class KnowledgeBaseFileService(
    BaseService[KnowledgeBaseFile, KnowledgeBaseFileCreate, PydanticBaseModel]
):
    model = KnowledgeBaseFile

    @classmethod
    async def get_files_by_kb(
        cls, db: AsyncSession, kb_id: str
    ) -> List[KnowledgeBaseFile]:
        query = (
            select(cls.model)
            .where(
                cls.model.kb_id == kb_id,
                cls.model.is_deleted == False,
            )
            .order_by(cls.model.sys_create_datetime.desc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def update_file_graph_status(
        cls, db: AsyncSession, file_id: str, has_graph: bool
    ):
        file = await cls.get_by_id(db, file_id)
        if file:
            file.has_graph = has_graph
            await db.flush()
            return file
        return None

    @classmethod
    async def count_by_kb(cls, db: AsyncSession, kb_id: str) -> int:
        from sqlalchemy import func
        query = (
            select(func.count(cls.model.id))
            .where(
                cls.model.kb_id == kb_id,
                cls.model.is_deleted == False,
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0


class KnowledgeGraphService(
    BaseService[KnowledgeGraph, KnowledgeGraphCreate, PydanticBaseModel]
):
    model = KnowledgeGraph

    @classmethod
    async def get_by_file(cls, db: AsyncSession, file_id: str) -> Optional[KnowledgeGraph]:
        query = select(cls.model).where(
            cls.model.file_id == file_id,
            cls.model.is_deleted == False,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def delete_by_file(cls, db: AsyncSession, file_id: str) -> bool:
        graph = await cls.get_by_file(db, file_id)
        if graph:
            await cls.delete(db, graph.id)
            return True
        return False
