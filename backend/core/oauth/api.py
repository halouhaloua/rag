#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: api.py
@Desc: OAuth API - OAuth 接口层 - 提供第三方 OAuth 登录的 API 接口
"""
"""
OAuth API - OAuth 接口层
提供第三方 OAuth 登录的 API 接口
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from core.oauth.schema import OAuthCallbackIn, OAuthLoginOut, AuthorizeUrlOut
from core.oauth.service import OAUTH_PROVIDERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=['OAuth登录'])

# 注意：路由路径不要重复添加 /oauth 前缀


def get_client_ip(request: Request) -> str:
    """获取客户端 IP 地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/{provider}/authorize", response_model=AuthorizeUrlOut, summary="获取 OAuth 授权 URL")
async def get_oauth_authorize_url(
    provider: str,
    state: str = Query(default='', description="状态参数，用于防止 CSRF 攻击"),
):
    """
    获取 OAuth 授权 URL (通用接口)
    
    Args:
        provider: OAuth 提供商 (gitee/github/qq/google/wechat/microsoft/dingtalk/feishu)
    
    前端应该将用户重定向到此 URL
    """
    # 验证 provider
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"不支持的 OAuth 提供商: {provider}")

    try:
        service_class = OAUTH_PROVIDERS[provider]
        authorize_url = service_class.get_authorize_url(state)

        return AuthorizeUrlOut(authorize_url=authorize_url)
    except Exception as e:
        logger.error(f"获取 {provider} 授权 URL 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取授权 URL 失败: {str(e)}")


@router.post("/{provider}/callback", response_model=OAuthLoginOut, summary="OAuth 回调处理")
async def oauth_callback(
    request: Request,
    provider: str,
    data: OAuthCallbackIn,
    db: AsyncSession = Depends(get_db),
):
    """
    处理 OAuth 回调 (通用接口)
    
    Args:
        provider: OAuth 提供商 (gitee/github/qq/google/wechat/microsoft/dingtalk/feishu)
        data: 回调数据（包含 code 和 state）
    
    前端在授权后会获得 code，将 code 发送到此接口完成登录
    """
    # 验证 provider
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"不支持的 OAuth 提供商: {provider}")

    try:
        service_class = OAUTH_PROVIDERS[provider]

        # 获取客户端 IP 和 User-Agent
        ip_address = get_client_ip(request)
        user_agent = request.headers.get('User-Agent', '')

        # 处理 OAuth 登录（传递 provider 作为登录方式）
        user, access_token, refresh_token, expire_time = await service_class.handle_oauth_login(
            db=db,
            code=data.code,
            ip_address=ip_address,
            user_agent=user_agent,
            login_type=provider
        )

        # 构造返回数据
        user_info = {
            'id': str(user.id),
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'avatar': user.avatar,
            'user_type': user.user_type,
            'is_superuser': user.is_superuser,
        }

        logger.info(f"{provider.capitalize()} OAuth 登录成功: {user.username}")

        return OAuthLoginOut(
            access_token=access_token,
            refresh_token=refresh_token,
            expire=expire_time,
            user_info=user_info,
        )

    except ValueError as e:
        logger.warning(f"{provider.capitalize()} OAuth 登录失败: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"{provider.capitalize()} OAuth 登录异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="登录失败，请稍后重试")
