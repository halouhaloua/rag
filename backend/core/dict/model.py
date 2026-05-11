#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: model.py
@Desc: Dict Model - 字典模型 - 用于管理系统字典数据
"""
"""
Dict Model - 字典模型
用于管理系统字典数据
"""
from sqlalchemy import Column, String, Boolean, Text

from app.base_model import BaseModel


class Dict(BaseModel):
    """
    系统字典表
    
    字段说明：
    - name: 字典名称
    - code: 字典编码（唯一）
    - status: 状态
    - remark: 备注
    """
    __tablename__ = "core_dict"
    
    # 字典名称
    name = Column(String(100), nullable=False, index=True, comment="字典名称")
    
    # 字典编码
    code = Column(String(100), unique=True, nullable=False, index=True, comment="字典编码")
    
    # 状态
    status = Column(Boolean, default=True, index=True, comment="状态")
    
    # 备注
    remark = Column(Text, nullable=True, comment="备注")
    
    def __str__(self):
        return f"{self.name} ({self.code})"
