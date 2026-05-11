#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: base_schema.py
@Desc: 通用分页响应模型 - items: List[T]
"""
from typing import Generic, TypeVar, List, Optional

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应模型"""
    items: List[T]
    total: int


class ResponseModel(BaseModel):
    """通用响应模型"""
    message: str = "success"
    data: Optional[dict | list] = None
