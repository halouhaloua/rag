#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: model.py
@Desc: 带缓存的Demo模型 - __tablename__ = "demo_cache"
"""
from sqlalchemy import Column, String, Text, Boolean

from app.base_model import BaseModel


class DemoCache(BaseModel):
    """带缓存的Demo模型"""
    __tablename__ = "demo_cache"

    title = Column(String(100), nullable=False, index=True, comment="标题")
    content = Column(Text, nullable=True, comment="内容")
    is_active = Column(Boolean, default=True, comment="是否激活")
