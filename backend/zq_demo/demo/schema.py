#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: schema.py
@Desc: Demo基础Schema - title: str
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DemoBase(BaseModel):
    """Demo基础Schema"""
    title: str
    content: Optional[str] = None
    is_active: bool = True


class DemoCreate(DemoBase):
    """创建Demo的Schema"""
    pass


class DemoUpdate(BaseModel):
    """更新Demo的Schema"""
    title: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


class DemoResponse(DemoBase):
    """Demo响应Schema"""
    id: str
    sort: int = 0
    is_deleted: bool = False
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
