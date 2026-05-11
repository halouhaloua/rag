#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: __init__.py
@Desc: 用户模块
"""
"""
用户模块
"""
from core.user.model import User
from core.user.service import UserService

__all__ = ["User", "UserService"]
