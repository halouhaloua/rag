#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: __init__.py
@Desc: Permission Module - 权限管理模块
"""
"""
Permission Module - 权限管理模块
"""
from core.permission.model import Permission
from core.permission.service import PermissionService
from core.permission.api import router

__all__ = ["Permission", "PermissionService", "router"]
