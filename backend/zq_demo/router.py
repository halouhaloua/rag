#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: router.py
@Desc: zq_demo模块统一路由
"""
"""
zq_demo模块统一路由
"""
from fastapi import APIRouter

from zq_demo.demo.api import router as demo_router
from zq_demo.demo_cache.api import router as demo_cache_router

router = APIRouter()

# 注册子模块路由
router.include_router(demo_router, prefix="/demo", tags=["Demo"])
router.include_router(demo_cache_router, prefix="/demo-cache", tags=["DemoCache"])
