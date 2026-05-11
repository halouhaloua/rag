#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: router.py
@Desc: Scheduler Router - 定时任务模块路由
"""
"""
Scheduler Router - 定时任务模块路由
"""
from fastapi import APIRouter

from scheduler.api import router as scheduler_router

router = APIRouter()

# 注册调度器路由
router.include_router(scheduler_router)
