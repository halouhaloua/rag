#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: schema.py
@Desc: 消息中心 Schema
"""
"""
消息中心 Schema
"""
from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, ConfigDict


# ============ 消息相关 Schema ============
class MessageOut(BaseModel):
    """消息输出"""
    id: str
    title: str
    content: str
    msg_type: str
    status: str
    link_type: str = ""
    link_id: str = ""
    sender_name: str = ""
    read_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(None, alias="sys_create_datetime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MessageListOut(BaseModel):
    """消息列表输出"""
    id: str
    title: str
    content: str
    msg_type: str
    status: str
    link_type: str = ""
    link_id: str = ""
    created_at: Optional[datetime] = Field(None, alias="sys_create_datetime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UnreadCountOut(BaseModel):
    """未读数量输出"""
    total: int
    by_type: Dict[str, int]


class MarkReadInput(BaseModel):
    """标记已读输入"""
    msg_type: Optional[str] = Field(None, description="消息类型，不传则标记全部")


# ============ 公告相关 Schema ============
class AnnouncementCreate(BaseModel):
    """创建公告"""
    title: str = Field(..., max_length=200, description="公告标题")
    content: str = Field(..., description="公告内容")
    summary: str = Field(default="", max_length=500, description="摘要")
    status: str = Field(default="draft", description="状态: draft/published")
    priority: int = Field(default=0, description="优先级: 0普通/1重要/2紧急")
    is_top: bool = Field(default=False, description="是否置顶")
    target_type: str = Field(default="all", description="接收范围: all/dept/role/user")
    target_ids: List[str] = Field(default=[], description="接收目标ID列表")
    publish_time: Optional[datetime] = Field(None, description="发布时间")
    expire_time: Optional[datetime] = Field(None, description="过期时间")


class AnnouncementUpdate(BaseModel):
    """更新公告"""
    title: Optional[str] = Field(None, max_length=200, description="公告标题")
    content: Optional[str] = Field(None, description="公告内容")
    summary: Optional[str] = Field(None, max_length=500, description="摘要")
    status: Optional[str] = Field(None, description="状态")
    priority: Optional[int] = Field(None, description="优先级")
    is_top: Optional[bool] = Field(None, description="是否置顶")
    target_type: Optional[str] = Field(None, description="接收范围")
    target_ids: Optional[List[str]] = Field(None, description="接收目标ID列表")
    publish_time: Optional[datetime] = Field(None, description="发布时间")
    expire_time: Optional[datetime] = Field(None, description="过期时间")


class AnnouncementOut(BaseModel):
    """公告输出"""
    id: str
    title: str
    content: str
    summary: str = ""
    status: str
    priority: int
    is_top: bool
    target_type: str
    target_ids: List[str] = []
    publish_time: Optional[datetime] = None
    expire_time: Optional[datetime] = None
    publisher_id: Optional[str] = None
    publisher_name: str = ""
    read_count: int = 0
    created_at: Optional[datetime] = Field(None, alias="sys_create_datetime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AnnouncementListOut(BaseModel):
    """公告列表输出"""
    id: str
    title: str
    summary: str = ""
    status: str
    priority: int
    is_top: bool
    target_type: str
    publisher_name: str = ""
    read_count: int = 0
    publish_time: Optional[datetime] = None
    created_at: Optional[datetime] = Field(None, alias="sys_create_datetime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserAnnouncementOut(BaseModel):
    """用户公告输出"""
    id: str
    title: str
    summary: str = ""
    content: str
    priority: int
    is_top: bool
    is_read: bool = False
    publisher_name: str = ""
    publish_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReadStatsOut(BaseModel):
    """阅读统计输出"""
    total_read: int
    readers: List[dict]
