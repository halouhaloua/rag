#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: router.py
@Desc: WebSocket 路由 - 定义 WebSocket 端点
"""
"""
WebSocket 路由
定义 WebSocket 端点
"""
from fastapi import APIRouter, WebSocket

from core.websocket.consumers import (
    TestWebSocketConsumer,
    NotificationConsumer,
    ServerMonitorConsumer,
    RedisMonitorConsumer,
    DatabaseMonitorConsumer,
)

router = APIRouter(redirect_slashes=False)


@router.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """WebSocket测试连接"""
    consumer = TestWebSocketConsumer(websocket)
    await consumer.run()


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """通知推送连接"""
    consumer = NotificationConsumer(websocket)
    await consumer.run()


@router.websocket("/ws/notification")
async def websocket_notification(websocket: WebSocket):
    """通知推送连接（兼容路径）"""
    consumer = NotificationConsumer(websocket)
    await consumer.run()


@router.websocket("/ws/notification/")
async def websocket_notification_slash(websocket: WebSocket):
    """通知推送连接（带斜杠兼容）"""
    consumer = NotificationConsumer(websocket)
    await consumer.run()


@router.websocket("/ws/server-monitor")
async def websocket_server_monitor(websocket: WebSocket):
    """服务器监控连接"""
    consumer = ServerMonitorConsumer(websocket)
    await consumer.run()


@router.websocket("/ws/redis-monitor")
async def websocket_redis_monitor(websocket: WebSocket):
    """Redis监控连接"""
    consumer = RedisMonitorConsumer(websocket)
    await consumer.run()


@router.websocket("/ws/database-monitor")
async def websocket_database_monitor(websocket: WebSocket):
    """数据库监控连接"""
    consumer = DatabaseMonitorConsumer(websocket)
    await consumer.run()
