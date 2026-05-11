#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: model.py
@Desc: Demo模型 - __tablename__ = "demos"
"""
from sqlalchemy import Column, String, Text, Boolean

from app.base_model import BaseModel


class Demo(BaseModel):
    """Demo模型"""
    __tablename__ = "demos"

    title = Column(String(100), nullable=False, comment="标题")
    content = Column(Text, nullable=True, comment="内容")
    is_active = Column(Boolean, default=True, comment="是否激活")
