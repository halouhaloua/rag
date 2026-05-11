#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: service.py
@Desc: 带缓存的Demo服务层 - 演示如何使用CacheService基类
"""
"""
带缓存的Demo服务层
演示如何使用CacheService基类
"""
from io import BytesIO
from typing import Tuple, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache_service import CacheService
from zq_demo.demo_cache.model import DemoCache
from zq_demo.demo_cache.schema import DemoCacheCreate, DemoCacheUpdate


class DemoCacheService(CacheService[DemoCache, DemoCacheCreate, DemoCacheUpdate]):
    """
    带缓存的Demo服务层
    继承CacheService，自动获得带缓存的增删改查功能
    """
    
    model = DemoCache
    
    # 缓存配置
    cache_prefix = "demo_cache:"
    cache_expire = 300
    
    # Excel导入导出配置
    excel_columns = {
        "title": "标题",
        "content": "内容",
        "is_active": "是否激活",
    }
    excel_sheet_name = "DemoCache列表"
    
    @classmethod
    def _serialize_for_cache(cls, item: Any) -> Dict[str, Any]:
        """自定义序列化方法，添加业务字段"""
        data = super()._serialize_for_cache(item)
        data.update({
            "title": item.title,
            "content": item.content,
            "is_active": item.is_active,
        })
        return data
    
    @classmethod
    def _export_converter(cls, item: Any) -> Dict[str, Any]:
        """导出数据转换器"""
        return {
            "title": item.title,
            "content": item.content or "",
            "is_active": "是" if item.is_active else "否",
        }
    
    @classmethod
    def _import_processor(cls, row: Dict[str, Any]) -> Optional[DemoCache]:
        """导入数据处理器"""
        title = row.get("title")
        if not title:
            return None
        
        is_active_str = row.get("is_active", "是")
        is_active = is_active_str in ("是", "true", "True", "1", True)
        
        return DemoCache(
            title=str(title),
            content=str(row.get("content") or ""),
            is_active=is_active
        )
    
    @classmethod
    async def export_to_excel(
        cls,
        db: AsyncSession,
        data_converter: Any = None
    ) -> BytesIO:
        """导出所有DemoCache到Excel"""
        return await super().export_to_excel(db, cls._export_converter)
    
    @classmethod
    async def import_from_excel(
        cls,
        db: AsyncSession,
        file_content: bytes,
        row_processor: Any = None
    ) -> Tuple[int, int]:
        """从Excel导入DemoCache"""
        return await super().import_from_excel(db, file_content, cls._import_processor)
