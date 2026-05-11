#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: tasks.py
@Desc: Scheduler Tasks - 定时任务函数示例 - 定义可被调度器调用的任务函数
"""
"""
Scheduler Tasks - 定时任务函数示例
定义可被调度器调用的任务函数
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def test_task(job_code: str = None, word: str = None, **kwargs):
    """
    测试任务
    
    这是一个简单的测试任务，用于验证调度器是否正常工作。
    
    Args:
        job_code: 任务编码（由调度器自动传入）
        **kwargs: 其他参数
    """
    logger.info(f"[{job_code}-{word}] 测试任务执行开始: {datetime.now()}")
    
    # 模拟任务执行
    import asyncio
    await asyncio.sleep(1)
    
    logger.info(f"[{job_code}] 测试任务执行完成: {datetime.now()}")
    return f"测试任务执行成功: {datetime.now()}"


async def cleanup_task(job_code: str = None, days: int = 30, **kwargs):
    """
    清理任务
    
    清理过期的日志数据。
    
    Args:
        job_code: 任务编码（由调度器自动传入）
        days: 保留最近N天的数据
        **kwargs: 其他参数
    """
    logger.info(f"[{job_code}] 清理任务执行开始，保留最近 {days} 天数据")
    
    try:
        from datetime import timedelta
        from sqlalchemy import select, delete
        from app.database import AsyncSessionLocal
        from scheduler.model import SchedulerLog
        
        cutoff = datetime.now() - timedelta(days=days)
        
        async with AsyncSessionLocal() as db:
            # 删除过期日志
            result = await db.execute(
                select(SchedulerLog).where(SchedulerLog.start_time < cutoff)
            )
            logs = result.scalars().all()
            count = len(logs)
            
            for log in logs:
                await db.delete(log)
            
            await db.commit()
            
        logger.info(f"[{job_code}] 清理任务执行完成，删除了 {count} 条日志")
        return f"清理了 {count} 条过期日志"
    except Exception as e:
        logger.error(f"[{job_code}] 清理任务执行失败: {str(e)}")
        raise


def sync_test_task(job_code: str = None, **kwargs):
    """
    同步测试任务
    
    这是一个同步任务示例，用于演示同步任务的使用。
    
    Args:
        job_code: 任务编码（由调度器自动传入）
        **kwargs: 其他参数
    """
    import time
    
    logger.info(f"[{job_code}] 同步测试任务执行开始: {datetime.now()}")
    
    # 模拟任务执行
    time.sleep(1)
    
    logger.info(f"[{job_code}] 同步测试任务执行完成: {datetime.now()}")
    return f"同步测试任务执行成功: {datetime.now()}"
