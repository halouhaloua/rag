#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: __init__.py
@Desc: Role Module - 角色管理模块
"""
"""
Role Module - 角色管理模块
"""
from core.role.model import Role
from core.role.service import RoleService
from core.role.api import router

__all__ = ["Role", "RoleService", "router"]
