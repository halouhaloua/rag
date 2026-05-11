#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: __init__.py
@Desc: Post Module - 岗位管理模块
"""
"""
Post Module - 岗位管理模块
"""
from core.post.model import Post
from core.post.service import PostService
from core.post.api import router

__all__ = ["Post", "PostService", "router"]
