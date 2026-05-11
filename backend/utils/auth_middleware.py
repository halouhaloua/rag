#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: auth_middleware.py
@Desc: Auth Middleware - 全局认证和鉴权中间件 - 
"""
"""
Auth Middleware - 全局认证和鉴权中间件

功能：
1. 认证（Authentication）：验证JWT Token的有效性
2. 鉴权（Authorization）：基于API路径的动态权限检查
"""
from typing import List, Optional, Callable
import re

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from utils.security import verify_access_token


# 默认白名单路由（不需要认证）
DEFAULT_WHITE_LIST = [
    # 认证相关
    "/api/core/login",
    "/api/core/refresh_token",
    # 文档相关
    "/docs",
    "/redoc",
    "/openapi.json",
    # 健康检查
    "/",
    "/health",
]

# OAuth白名单正则模式
OAUTH_WHITE_LIST_PATTERNS = [
    r"^/api/core/oauth/.*/authorize$",   # OAuth授权URL获取
    r"^/api/core/oauth/.*/callback$",    # OAuth回调处理
]

# WebSocket白名单正则模式（WebSocket自己处理Token认证）
WEBSOCKET_WHITE_LIST_PATTERNS = [
    r"^/ws/.*",  # 所有WebSocket路径
]

# 白名单正则模式（支持通配符）
DEFAULT_WHITE_LIST_PATTERNS = [
    r"^/docs.*",
    r"^/redoc.*",
    *OAUTH_WHITE_LIST_PATTERNS,  # OAuth相关接口
    *WEBSOCKET_WHITE_LIST_PATTERNS,  # WebSocket相关接口
]

# 允许使用Query参数传递Token的API路径模式（出于安全考虑，仅限特定接口）
# 主要用于文件下载、流式传输等无法设置Header的场景
QUERY_TOKEN_ALLOWED_PATTERNS = [
    r"^/api/core/file_manager/stream/.*",      # 文件流式传输
    r"^/api/core/file_manager/proxy/.*",       # 文件代理访问
    r"^/api/core/file_manager/file/download.*", # 文件下载
]


class AuthMiddleware(BaseHTTPMiddleware):
    """
    全局认证中间件
    
    功能：
    - 默认所有接口需要Bearer Token认证
    - 支持白名单配置（精确匹配和正则匹配）
    - 白名单内的接口无需认证
    """
    
    def __init__(
        self,
        app,
        white_list: Optional[List[str]] = None,
        white_list_patterns: Optional[List[str]] = None,
    ):
        """
        初始化中间件
        
        :param app: FastAPI应用
        :param white_list: 白名单路由列表（精确匹配）
        :param white_list_patterns: 白名单正则模式列表
        """
        super().__init__(app)
        self.white_list = set(white_list or DEFAULT_WHITE_LIST)
        self.white_list_patterns = [
            re.compile(p) for p in (white_list_patterns or DEFAULT_WHITE_LIST_PATTERNS)
        ]
    
    def is_white_listed(self, path: str) -> bool:
        """
        检查路径是否在白名单中
        
        :param path: 请求路径
        :return: 是否在白名单中
        """
        # 精确匹配
        if path in self.white_list:
            return True
        
        # 正则匹配
        for pattern in self.white_list_patterns:
            if pattern.match(path):
                return True
        
        return False
    
    def _is_query_token_allowed(self, path: str) -> bool:
        """
        检查路径是否允许使用Query参数传递Token
        
        出于安全考虑，仅允许特定接口使用Query Token
        """
        for pattern in [re.compile(p) for p in QUERY_TOKEN_ALLOWED_PATTERNS]:
            if pattern.match(path):
                return True
        return False

    def _extract_token(self, request: Request) -> str | None:
        """
        从请求中提取Token
        
        支持两种方式：
        1. Authorization Header: Bearer <token>（所有接口）
        2. Query参数: ?token=<token>（仅限特定接口，如文件下载）
        
        :param request: 请求对象
        :return: Token字符串或None
        """
        # 优先从Authorization头获取
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1]
        
        # Query参数方式仅限特定接口
        path = request.url.path
        if self._is_query_token_allowed(path):
            token = request.query_params.get("token")
            if token:
                return token
        
        return None

    async def dispatch(self, request: Request, call_next: Callable):
        """
        处理请求
        
        :param request: 请求对象
        :param call_next: 下一个处理函数
        :return: 响应
        """
        path = request.url.path
        
        # 白名单路由直接放行
        if self.is_white_listed(path):
            return await call_next(request)
        
        # OPTIONS请求放行（CORS预检）
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # 提取Token（支持Header和Query两种方式）
        token = self._extract_token(request)
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "未提供认证凭据"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 验证Token
        payload = verify_access_token(token)
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "无效或过期的Token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 将用户信息存入request.state，供后续使用
        request.state.user_id = payload.get("sub")
        request.state.username = payload.get("username")
        request.state.role_id = payload.get("role_id")
        request.state.is_superuser = payload.get("is_superuser", False)
        request.state.token_payload = payload
        
        return await call_next(request)


class AuthPermissionMiddleware(BaseHTTPMiddleware):
    """
    全局认证和鉴权中间件
    
    功能：
    - 认证：验证JWT Token的有效性
    - 鉴权：基于API路径的动态权限检查
    
    工作流程：
    1. 检查是否在白名单中，是则直接放行
    2. 验证JWT Token，获取用户信息
    3. 根据请求的API路径和方法，查找Permission表中是否有对应的权限记录
    4. 如果有权限记录，检查用户的角色是否关联了该权限
    5. 如果用户角色有该权限，则放行；否则返回403
    6. 如果Permission表中没有该API的权限记录，则默认放行
    """
    
    def __init__(
        self,
        app,
        white_list: Optional[List[str]] = None,
        white_list_patterns: Optional[List[str]] = None,
        enable_permission_check: bool = True,
    ):
        """
        初始化中间件
        
        :param app: FastAPI应用
        :param white_list: 白名单路由列表（精确匹配）
        :param white_list_patterns: 白名单正则模式列表
        :param enable_permission_check: 是否启用权限检查（默认True）
        """
        super().__init__(app)
        self.white_list = set(white_list or DEFAULT_WHITE_LIST)
        self.white_list_patterns = [
            re.compile(p) for p in (white_list_patterns or DEFAULT_WHITE_LIST_PATTERNS)
        ]
        self.enable_permission_check = enable_permission_check
    
    def is_white_listed(self, path: str) -> bool:
        """检查路径是否在白名单中"""
        if path in self.white_list:
            return True
        
        for pattern in self.white_list_patterns:
            if pattern.match(path):
                return True
        
        return False
    
    def _is_query_token_allowed(self, path: str) -> bool:
        """
        检查路径是否允许使用Query参数传递Token
        
        出于安全考虑，仅允许特定接口使用Query Token
        """
        for pattern in [re.compile(p) for p in QUERY_TOKEN_ALLOWED_PATTERNS]:
            if pattern.match(path):
                return True
        return False

    def _extract_token(self, request: Request) -> str | None:
        """
        从请求中提取Token
        
        支持两种方式：
        1. Authorization Header: Bearer <token>（所有接口）
        2. Query参数: ?token=<token>（仅限特定接口，如文件下载）
        """
        # 优先从Authorization头获取
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1]
        
        # Query参数方式仅限特定接口
        path = request.url.path
        if self._is_query_token_allowed(path):
            token = request.query_params.get("token")
            if token:
                return token
        
        return None
    
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求"""
        path = request.url.path
        method = request.method
        
        # 白名单路由直接放行
        if self.is_white_listed(path):
            return await call_next(request)
        
        # OPTIONS请求放行（CORS预检）
        if method == "OPTIONS":
            return await call_next(request)
        
        # ========== 认证（Authentication）==========
        token = self._extract_token(request)
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "未提供认证凭据"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        payload = verify_access_token(token)
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "无效或过期的Token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 将用户信息存入request.state
        user_id = payload.get("sub")
        role_id = payload.get("role_id")
        is_superuser = payload.get("is_superuser", False)
        
        request.state.user_id = user_id
        request.state.username = payload.get("username")
        request.state.role_id = role_id
        request.state.is_superuser = is_superuser
        request.state.token_payload = payload
        
        # ========== 鉴权（Authorization）==========
        if self.enable_permission_check:
            # 超级管理员跳过权限检查
            if not is_superuser:
                from app.database import async_session_maker
                from utils.permission import check_api_permission
                
                async with async_session_maker() as db:
                    has_permission, error_msg = await check_api_permission(
                        db=db,
                        user_id=user_id,
                        role_id=role_id,
                        is_superuser=is_superuser,
                        request_path=path,
                        http_method=method,
                    )
                    
                    if not has_permission:
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={"detail": error_msg or "权限不足"},
                        )
        
        return await call_next(request)


def get_auth_middleware(
    white_list: Optional[List[str]] = None,
    white_list_patterns: Optional[List[str]] = None,
    enable_permission_check: bool = False,
) -> type:
    """
    获取配置好的认证中间件类（不带权限检查）
    
    使用方式：
    app.add_middleware(get_auth_middleware(white_list=["/public"]))
    
    :param white_list: 额外的白名单路由
    :param white_list_patterns: 额外的白名单正则模式
    :param enable_permission_check: 是否启用权限检查
    :return: 配置好的中间件类
    """
    merged_white_list = list(DEFAULT_WHITE_LIST)
    if white_list:
        merged_white_list.extend(white_list)
    
    merged_patterns = list(DEFAULT_WHITE_LIST_PATTERNS)
    if white_list_patterns:
        merged_patterns.extend(white_list_patterns)
    
    if enable_permission_check:
        class ConfiguredMiddleware(AuthPermissionMiddleware):
            def __init__(self, app):
                super().__init__(
                    app,
                    white_list=merged_white_list,
                    white_list_patterns=merged_patterns,
                    enable_permission_check=True,
                )
    else:
        class ConfiguredMiddleware(AuthMiddleware):
            def __init__(self, app):
                super().__init__(
                    app,
                    white_list=merged_white_list,
                    white_list_patterns=merged_patterns,
                )
    
    return ConfiguredMiddleware


def get_auth_permission_middleware(
    white_list: Optional[List[str]] = None,
    white_list_patterns: Optional[List[str]] = None,
) -> type:
    """
    获取配置好的认证+鉴权中间件类
    
    使用方式：
    app.add_middleware(get_auth_permission_middleware(white_list=["/public"]))
    
    :param white_list: 额外的白名单路由
    :param white_list_patterns: 额外的白名单正则模式
    :return: 配置好的中间件类
    """
    return get_auth_middleware(
        white_list=white_list,
        white_list_patterns=white_list_patterns,
        enable_permission_check=True,
    )
