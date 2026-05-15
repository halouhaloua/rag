from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from core.role.model import Role as RoleModel
from core.user.model import User
from utils.security import get_current_user

from graphrag.kb_manager.schema import (
    RoleInfo,
    KBPermissionUpdateRequest,
    KBAccessCheckResponse,
)
from graphrag.kb_manager.service import KnowledgeBasePermissionService
from graphrag.rag.schema import KnowledgeBaseListResponse
from graphrag.rag.db_service import KnowledgeBaseService

router = APIRouter(
    prefix="/api/knowledge-base",
    tags=["知识库权限管理"],
)


@router.get(
    "/roles",
    response_model=List[RoleInfo],
    summary="获取所有角色（用于KB权限分配）",
)
async def list_roles_for_permission(db: AsyncSession = Depends(get_db)):
    query = select(RoleModel).where(
        RoleModel.is_deleted == False,
        RoleModel.status == True,
    ).order_by(RoleModel.priority.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/role/{role_id}/kb-permissions",
    response_model=KnowledgeBaseListResponse,
    summary="获取角色已分配的知识库列表",
)
async def get_role_kb_permissions(
    role_id: str,
    db: AsyncSession = Depends(get_db),
):
    kb_ids = await KnowledgeBasePermissionService.get_role_kb_ids(db, role_id)
    if not kb_ids:
        return KnowledgeBaseListResponse(items=[], total=0)

    from sqlalchemy import func as sa_func
    from graphrag.rag.model import KnowledgeBaseFile

    query = (
        select(KnowledgeBaseService.model)
        .where(
            KnowledgeBaseService.model.id.in_(kb_ids),
            KnowledgeBaseService.model.is_deleted == False,
        )
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    for item in items:
        count_query = (
            select(sa_func.count(KnowledgeBaseFile.id))
            .where(
                KnowledgeBaseFile.kb_id == item.id,
                KnowledgeBaseFile.is_deleted == False,
            )
        )
        cnt = await db.execute(count_query)
        item.file_count = cnt.scalar() or 0

    return KnowledgeBaseListResponse(items=items, total=len(items))


@router.put(
    "/role/{role_id}/kb-permissions",
    summary="更新角色的知识库权限",
)
async def update_role_kb_permissions(
    role_id: str,
    data: KBPermissionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅超级管理员可管理知识库权限")
    await KnowledgeBasePermissionService.set_role_kbs(db, role_id, data.kb_ids)
    return {"msg": "权限更新成功"}


@router.get(
    "/kb-access-check/{kb_id}",
    response_model=KBAccessCheckResponse,
    summary="验证当前用户是否有权访问指定知识库",
)
async def check_kb_access(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_access = await KnowledgeBasePermissionService.check_kb_access(
        db, kb_id, current_user
    )
    return KBAccessCheckResponse(has_access=has_access)
