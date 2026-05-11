#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: schema.py
@Desc: DemoCache基础Schema - title: str = Field(..., min_length=1, max_length=100, description="标题")
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DemoCacheBase(BaseModel):
    """DemoCache基础Schema"""
    title: str = Field(..., min_length=1, max_length=100, description="标题")
    content: Optional[str] = Field(default=None, description="内容")
    is_active: bool = Field(default=True, description="是否激活")


class DemoCacheCreate(DemoCacheBase):
    """创建DemoCache的Schema"""
    pass


class DemoCacheUpdate(BaseModel):
    """更新DemoCache的Schema"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=100, description="标题")
    content: Optional[str] = Field(default=None, description="内容")
    is_active: Optional[bool] = Field(default=None, description="是否激活")


class DemoCacheResponse(DemoCacheBase):
    """DemoCache响应Schema"""
    id: str
    sort: int
    is_deleted: bool
    sys_create_datetime: datetime
    sys_update_datetime: datetime

    class Config:
        from_attributes = True
