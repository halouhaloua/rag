#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: api.py
@Desc: 带缓存的Demo API接口 - 演示如何在API层使用带缓存的Service
"""
"""
带缓存的Demo API接口
演示如何在API层使用带缓存的Service
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.base_schema import PaginatedResponse, ResponseModel
from zq_demo.demo_cache.schema import DemoCacheCreate, DemoCacheUpdate, DemoCacheResponse
from zq_demo.demo_cache.service import DemoCacheService

router = APIRouter(prefix="/demo-cache", tags=["DemoCache管理（带缓存）"])


@router.post("/", response_model=DemoCacheResponse, summary="创建DemoCache")
async def create_demo_cache(demo: DemoCacheCreate, db: AsyncSession = Depends(get_db)):
    """
    创建新DemoCache
    - **title**: 标题
    - **content**: 内容（可选）
    - **is_active**: 是否激活（默认true）
    """
    # 检查标题唯一性
    if not await DemoCacheService.check_unique(db, field="title", value=demo.title):
        raise HTTPException(status_code=400, detail="标题已存在")
    
    return await DemoCacheService.create(db=db, data=demo)


@router.get("/", response_model=PaginatedResponse[DemoCacheResponse], summary="获取DemoCache列表")
async def get_demo_caches(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=settings.PAGE_SIZE, ge=1, le=settings.PAGE_MAX_SIZE, alias="pageSize", description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取DemoCache列表（分页，优先从缓存获取）
    """
    items, total = await DemoCacheService.get_list(db, page=page, page_size=page_size)
    return PaginatedResponse(items=items, total=total)


@router.get("/export/excel", summary="导出Excel")
async def export_excel(db: AsyncSession = Depends(get_db)):
    """
    导出所有DemoCache数据到Excel
    """
    output = await DemoCacheService.export_to_excel(db)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=demo_cache_export.xlsx"}
    )


@router.get("/import/template", summary="下载导入模板")
async def download_template():
    """
    下载Excel导入模板
    """
    output = DemoCacheService.get_import_template()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=demo_cache_template.xlsx"}
    )


@router.post("/import/excel", response_model=ResponseModel, summary="导入Excel")
async def import_excel(
    file: UploadFile = File(..., description="Excel文件(.xlsx)"),
    db: AsyncSession = Depends(get_db)
):
    """
    从Excel导入DemoCache数据
    """
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="只支持.xlsx格式的Excel文件")
    
    content = await file.read()
    success_count, fail_count = await DemoCacheService.import_from_excel(db, content)
    
    return ResponseModel(
        message=f"导入完成，成功{success_count}条，失败{fail_count}条",
        data={"success": success_count, "fail": fail_count}
    )


@router.get("/check/unique", response_model=ResponseModel, summary="检查字段唯一性")
async def check_unique(
    field: str = Query(..., description="字段名，如title"),
    value: str = Query(..., description="字段值"),
    exclude_id: str = Query(default=None, alias="excludeId", description="排除的记录ID（更新时使用）"),
    db: AsyncSession = Depends(get_db)
):
    """
    检查字段值是否唯一
    """
    allowed_fields = ["title"]
    if field not in allowed_fields:
        raise HTTPException(status_code=400, detail=f"不支持检查字段: {field}，允许的字段: {allowed_fields}")
    
    is_unique = await DemoCacheService.check_unique(db, field=field, value=value, exclude_id=exclude_id)
    return ResponseModel(
        message="字段值可用" if is_unique else "字段值已存在",
        data={"unique": is_unique}
    )


@router.post("/cache/clear", response_model=ResponseModel, summary="清除缓存")
async def clear_cache(
    record_id: str = Query(default=None, alias="recordId", description="指定ID则只清除该记录缓存，否则清除所有缓存")
):
    """
    手动清除缓存
    - 不传recordId：清除所有DemoCache缓存
    - 传recordId：只清除指定记录的缓存
    """
    count = await DemoCacheService.clear_cache(record_id)
    return ResponseModel(
        message=f"已清除{count}个缓存",
        data={"cleared": count}
    )


@router.get("/cache/stats/{record_id}", response_model=ResponseModel, summary="获取缓存状态")
async def get_cache_stats(record_id: str):
    """
    获取指定记录的缓存状态信息
    """
    stats = await DemoCacheService.get_cache_stats(record_id)
    return ResponseModel(
        message="获取成功",
        data=stats
    )


@router.get("/{record_id}", response_model=DemoCacheResponse, summary="获取单个DemoCache")
async def get_demo_cache(record_id: str, db: AsyncSession = Depends(get_db)):
    """
    根据ID获取DemoCache详情（优先从缓存获取）
    """
    db_demo = await DemoCacheService.get_by_id(db, record_id=record_id)
    if db_demo is None:
        raise HTTPException(status_code=404, detail="DemoCache不存在")
    return db_demo


@router.get("/{record_id}/no-cache", response_model=DemoCacheResponse, summary="获取单个DemoCache（不使用缓存）")
async def get_demo_cache_no_cache(record_id: str, db: AsyncSession = Depends(get_db)):
    """
    根据ID获取DemoCache详情（强制从数据库获取，不使用缓存）
    """
    db_demo = await DemoCacheService.get_by_id_no_cache(db, record_id=record_id)
    if db_demo is None:
        raise HTTPException(status_code=404, detail="DemoCache不存在")
    return db_demo


@router.put("/{record_id}", response_model=DemoCacheResponse, summary="全量更新DemoCache")
async def update_demo_cache(record_id: str, demo: DemoCacheUpdate, db: AsyncSession = Depends(get_db)):
    """
    全量更新DemoCache信息
    """
    # 检查标题唯一性（排除自身）
    if demo.title and not await DemoCacheService.check_unique(db, field="title", value=demo.title, exclude_id=record_id):
        raise HTTPException(status_code=400, detail="标题已存在")
    
    db_demo = await DemoCacheService.update(db, record_id=record_id, data=demo)
    if db_demo is None:
        raise HTTPException(status_code=404, detail="DemoCache不存在")
    return db_demo


@router.patch("/{record_id}", response_model=DemoCacheResponse, summary="部分更新DemoCache")
async def patch_demo_cache(record_id: str, demo: DemoCacheUpdate, db: AsyncSession = Depends(get_db)):
    """
    部分更新DemoCache信息（只更新传入的字段）
    """
    # 检查标题唯一性（排除自身）
    if demo.title and not await DemoCacheService.check_unique(db, field="title", value=demo.title, exclude_id=record_id):
        raise HTTPException(status_code=400, detail="标题已存在")
    
    db_demo = await DemoCacheService.update(db, record_id=record_id, data=demo)
    if db_demo is None:
        raise HTTPException(status_code=404, detail="DemoCache不存在")
    return db_demo


@router.delete("/{record_id}", response_model=ResponseModel, summary="删除DemoCache")
async def delete_demo_cache(
    record_id: str,
    hard: bool = Query(default=False, description="是否物理删除，False为逻辑删除，True为物理删除"),
    db: AsyncSession = Depends(get_db)
):
    """
    删除DemoCache
    - **hard=false**: 逻辑删除（默认）
    - **hard=true**: 物理删除
    """
    success = await DemoCacheService.delete(db, record_id=record_id, hard=hard)
    if not success:
        raise HTTPException(status_code=404, detail="DemoCache不存在")
    return ResponseModel(message="删除成功")
