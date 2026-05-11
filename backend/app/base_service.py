#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: base_service.py
@Desc: 通用服务基类 - 提供增删改查和Excel导入导出的通用实现
"""
from io import BytesIO
from typing import TypeVar, Generic, Type, Optional, List, Tuple, Dict, Callable, Any, ClassVar

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.base_model import BaseModel as DBBaseModel
from utils.excel import ExcelHandler

T = TypeVar("T", bound=DBBaseModel)
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)


class BaseService(Generic[T, CreateSchema, UpdateSchema]):
    """
    通用服务基类
    提供增删改查和Excel导入导出的通用实现
    """
    
    # 子类必须定义
    model: ClassVar[Type[DBBaseModel]]
    
    # Excel导入导出列映射，子类可覆盖
    excel_columns: ClassVar[Dict[str, str]]
    excel_sheet_name: ClassVar[str]
    
    @classmethod
    async def create(cls, db: AsyncSession, data: CreateSchema, auto_commit: bool = True) -> Any:
        """
        创建记录
        
        :param db: 数据库会话
        :param data: 创建数据Schema
        :param auto_commit: 是否自动提交，默认True。在事务中使用时设为False
        :return: 创建的记录
        """
        db_obj = cls.model(**data.model_dump())
        db.add(db_obj)
        if auto_commit:
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.flush()
            await db.refresh(db_obj)
        return db_obj
    
    @classmethod
    async def get_by_id(cls, db: AsyncSession, record_id: str) -> Optional[Any]:
        """
        根据ID获取单条记录（排除已删除）
        
        :param db: 数据库会话
        :param record_id: 记录ID
        :return: 记录或None
        """
        result = await db.execute(
            select(cls.model).where(
                cls.model.id == record_id,
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_list(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[List[Any]] = None
    ) -> Tuple[List[Any], int]:
        """
        获取列表（分页，排除已删除）
        
        :param db: 数据库会话
        :param page: 页码
        :param page_size: 每页数量
        :param filters: 额外的过滤条件列表
        :return: (数据列表, 总数)
        """
        base_query = select(cls.model).where(cls.model.is_deleted == False)  # noqa: E712
        
        # 添加额外过滤条件
        if filters:
            for f in filters:
                base_query = base_query.where(f)
        
        # 获取总数
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0
        
        # 计算offset
        offset = (page - 1) * page_size
        
        # 获取分页数据
        result = await db.execute(
            base_query.order_by(
                desc(cls.model.sort),
                desc(cls.model.sys_create_datetime)
            )
            .offset(offset)
            .limit(page_size)
        )
        items = list(result.scalars().all())
        
        return items, total
    
    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        record_id: str,
        data: UpdateSchema,
        auto_commit: bool = True
    ) -> Optional[Any]:
        """
        更新记录
        
        :param db: 数据库会话
        :param record_id: 记录ID
        :param data: 更新数据Schema
        :param auto_commit: 是否自动提交，默认True。在事务中使用时设为False
        :return: 更新后的记录或None
        """
        db_obj = await cls.get_by_id(db, record_id)
        if not db_obj:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        if auto_commit:
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.flush()
            await db.refresh(db_obj)
        return db_obj
    
    @classmethod
    async def delete(
        cls,
        db: AsyncSession,
        record_id: str,
        hard: bool = False,
        auto_commit: bool = True
    ) -> bool:
        """
        删除记录
        
        :param db: 数据库会话
        :param record_id: 记录ID
        :param hard: True为物理删除，False为逻辑删除
        :param auto_commit: 是否自动提交，默认True。在事务中使用时设为False
        :return: 是否删除成功
        """
        db_obj = await cls.get_by_id(db, record_id)
        if not db_obj:
            return False
        
        if hard:
            await db.delete(db_obj)
        else:
            db_obj.is_deleted = True
        if auto_commit:
            await db.commit()
        else:
            await db.flush()
        return True
    
    @classmethod
    async def batch_delete(
        cls,
        db: AsyncSession,
        ids: List[str],
        hard: bool = False,
        auto_commit: bool = True
    ) -> Tuple[int, int]:
        """
        批量删除记录
        
        :param db: 数据库会话
        :param ids: 记录ID列表
        :param hard: True为物理删除，False为逻辑删除
        :param auto_commit: 是否自动提交，默认True。在事务中使用时设为False
        :return: (成功数, 失败数)
        """
        success_count = 0
        fail_count = 0
        
        for record_id in ids:
            db_obj = await cls.get_by_id(db, record_id)
            if db_obj:
                if hard:
                    await db.delete(db_obj)
                else:
                    db_obj.is_deleted = True
                success_count += 1
            else:
                fail_count += 1
        
        if success_count > 0:
            if auto_commit:
                await db.commit()
            else:
                await db.flush()
        
        return success_count, fail_count
    
    @classmethod
    async def export_to_excel(
        cls,
        db: AsyncSession,
        data_converter: Optional[Callable[[Any], Dict[str, Any]]] = None
    ) -> BytesIO:
        """
        导出数据到Excel
        
        :param db: 数据库会话
        :param data_converter: 数据转换函数，将model转为dict，子类可自定义
        :return: Excel文件的BytesIO对象
        """
        result = await db.execute(
            select(cls.model).where(cls.model.is_deleted == False)  # noqa: E712
            .order_by(desc(cls.model.sort), desc(cls.model.sys_create_datetime))
        )
        items = result.scalars().all()
        
        # 转换数据
        if data_converter:
            data = [data_converter(item) for item in items]
        else:
            # 默认转换：使用excel_columns中的字段
            data = [
                {field: getattr(item, field, "") for field in cls.excel_columns.keys()}
                for item in items
            ]
        
        return ExcelHandler.export_to_excel(data, cls.excel_columns, cls.excel_sheet_name)
    
    @classmethod
    async def import_from_excel(
        cls,
        db: AsyncSession,
        file_content: bytes,
        row_processor: Optional[Callable[[Dict[str, Any]], Optional[Any]]] = None
    ) -> Tuple[int, int]:
        """
        从Excel导入数据
        
        :param db: 数据库会话
        :param file_content: Excel文件内容
        :param row_processor: 行数据处理函数，将dict转为model实例，子类可自定义
        :return: (成功数, 失败数)
        """
        rows = ExcelHandler.import_from_excel(file_content, cls.excel_columns)
        
        success_count = 0
        fail_count = 0
        
        for row in rows:
            try:
                if row_processor:
                    db_obj = row_processor(row)
                else:
                    # 默认处理：直接创建model实例
                    db_obj = cls.model(**row)
                
                if db_obj:
                    db.add(db_obj)
                    success_count += 1
            except Exception:
                fail_count += 1
        
        if success_count > 0:
            await db.commit()
        
        return success_count, fail_count
    
    @classmethod
    def get_import_template(cls) -> BytesIO:
        """获取导入模板"""
        return ExcelHandler.generate_template(cls.excel_columns, cls.excel_sheet_name)
    
    @classmethod
    async def check_unique(
        cls,
        db: AsyncSession,
        field: str,
        value: Any,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        检查字段值是否唯一
        
        :param db: 数据库会话
        :param field: 字段名
        :param value: 字段值
        :param exclude_id: 排除的记录ID（用于更新时排除自身）
        :return: True表示唯一，False表示已存在
        """
        query = select(cls.model).where(
            getattr(cls.model, field) == value,
            cls.model.is_deleted == False  # noqa: E712
        )
        
        # 更新时排除自身
        if exclude_id:
            query = query.where(cls.model.id != exclude_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is None
    
    @classmethod
    async def get_by_field(
        cls,
        db: AsyncSession,
        field: str,
        value: Any
    ) -> Optional[Any]:
        """
        根据字段获取单条记录
        
        :param db: 数据库会话
        :param field: 字段名
        :param value: 字段值
        :return: 记录或None
        """
        result = await db.execute(
            select(cls.model).where(
                getattr(cls.model, field) == value,
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def exists(
        cls,
        db: AsyncSession,
        filters: List[Any]
    ) -> bool:
        """
        检查是否存在符合条件的记录
        
        :param db: 数据库会话
        :param filters: 过滤条件列表
        :return: True表示存在，False表示不存在
        """
        query = select(cls.model).where(cls.model.is_deleted == False)  # noqa: E712
        for f in filters:
            query = query.where(f)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
