#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: __init__.py
@Desc: 部门模块
"""
"""
部门模块
"""
from core.dept.model import Dept
from core.dept.service import DeptService

__all__ = ["Dept", "DeptService"]
