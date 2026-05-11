#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: schema.py
@Desc: Auth Schema - 认证相关Schema
"""
"""
Auth Schema - 认证相关Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token响应"""
    accessToken: str = Field(..., description="访问令牌")
    refreshToken: str = Field(..., description="刷新令牌")
    tokenType: str = Field(default="bearer", description="令牌类型")
    expireTime: int = Field(..., description="访问令牌过期时间（秒）")


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class TokenData(BaseModel):
    """Token数据"""
    user_id: Optional[str] = None
    username: Optional[str] = None


class LoginUserInfo(BaseModel):
    """登录用户信息"""
    id: str
    username: str
    name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    avatar: Optional[str] = None
    is_superuser: bool = False
    dept_id: Optional[str] = None
    user_type: int = 1
    user_status: int = 1


class LoginResponse(BaseModel):
    """登录响应"""
    user: LoginUserInfo = Field(..., description="用户信息")
    token: TokenResponse = Field(..., description="令牌信息")
