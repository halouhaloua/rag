#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: service.py
@Desc: Demo服务层 - 继承BaseService，自动获得增删改查和Excel导入导出功能
"""
from io import BytesIO
from typing import Tuple, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.base_service import BaseService
from zq_demo.demo.model import Demo
from zq_demo.demo.schema import DemoCreate, DemoUpdate


class DemoService(BaseService[Demo, DemoCreate, DemoUpdate]):
    """
    Demo服务层
    继承BaseService，自动获得增删改查和Excel导入导出功能
    """
    
    model = Demo
    
    # Excel导入导出配置
    excel_columns = {
        "title": "标题",
        "content": "内容",
        "is_active": "是否激活",
    }
    excel_sheet_name = "Demo列表"
    
    @classmethod
    def _export_converter(cls, item: Any) -> Dict[str, Any]:
        """导出数据转换器"""
        return {
            "title": item.title,
            "content": item.content or "",
            "is_active": "是" if item.is_active else "否",
        }
    
    @classmethod
    def _import_processor(cls, row: Dict[str, Any]) -> Optional[Demo]:
        """导入数据处理器"""
        title = row.get("title")
        if not title:
            return None
        
        is_active_str = row.get("is_active", "是")
        is_active = is_active_str in ("是", "true", "True", "1", True)
        
        return Demo(
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
        """导出所有Demo到Excel"""
        return await super().export_to_excel(db, cls._export_converter)
    
    @classmethod
    async def import_from_excel(
        cls,
        db: AsyncSession,
        file_content: bytes,
        row_processor: Any = None
    ) -> Tuple[int, int]:
        """从Excel导入Demo"""
        return await super().import_from_excel(db, file_content, cls._import_processor)
