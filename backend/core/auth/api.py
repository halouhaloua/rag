#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: api.py
@Desc: Auth API - 认证相关接口
"""
"""
Auth API - 认证相关接口
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.base_schema import ResponseModel
from utils.redis import RedisClient
from core.auth.schema import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LoginUserInfo,
)
from core.user.service import UserService
from core.login_log.service import LoginLogService
from utils.client_info import get_client_info
from utils.security import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    get_current_user,
)

router = APIRouter(prefix="", tags=["认证管理"])

# Redis中存储refresh token的key前缀
REFRESH_TOKEN_PREFIX = "refresh_token:"
# Redis中存储token黑名单的key前缀
TOKEN_BLACKLIST_PREFIX = "token_blacklist:"


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录（JSON格式，供前端使用）
    
    - **username**: 用户名
    - **password**: 密码
    
    返回access_token和refresh_token
    """
    # 获取客户端信息
    client_info = get_client_info(request)
    
    # 验证用户
    user = await UserService.authenticate(db, data.username, data.password)
    if not user:
        # 记录登录失败日志
        await LoginLogService.record_login(
            db=db,
            username=data.username,
            status=0,
            login_ip=client_info["login_ip"],
            failure_reason=2,  # 密码错误
            failure_message="用户名或密码错误",
            user_agent=client_info["user_agent"],
            browser_type=client_info["browser_type"],
            os_type=client_info["os_type"],
            device_type=client_info["device_type"],
            login_type="password",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户状态
    if not user.is_active:
        # 记录登录失败日志
        await LoginLogService.record_login(
            db=db,
            username=data.username,
            user_id=user.id,
            status=0,
            login_ip=client_info["login_ip"],
            failure_reason=3,  # 用户已禁用
            failure_message="用户已被禁用",
            user_agent=client_info["user_agent"],
            browser_type=client_info["browser_type"],
            os_type=client_info["os_type"],
            device_type=client_info["device_type"],
            login_type="password",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    if user.user_status != 1:
        status_msg = {0: "用户已禁用", 2: "用户已锁定"}.get(user.user_status, "用户状态异常")
        failure_reason = 3 if user.user_status == 0 else 4  # 3=禁用, 4=锁定
        # 记录登录失败日志
        await LoginLogService.record_login(
            db=db,
            username=data.username,
            user_id=user.id,
            status=0,
            login_ip=client_info["login_ip"],
            failure_reason=failure_reason,
            failure_message=status_msg,
            user_agent=client_info["user_agent"],
            browser_type=client_info["browser_type"],
            os_type=client_info["os_type"],
            device_type=client_info["device_type"],
            login_type="password",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=status_msg
        )
    
    # 生成token（包含角色信息）
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    token_data = {
        "sub": user.id,
        "username": user.username,
        "role_id": user.role_id,
        "is_superuser": user.is_superuser,
    }
    access_token = create_access_token(token_data, access_token_expires)
    refresh_token = create_refresh_token(token_data, refresh_token_expires)
    
    # 将refresh token存入Redis（用于验证和登出时失效）
    redis = await RedisClient.get_client()
    await redis.set(
        f"{REFRESH_TOKEN_PREFIX}{user.id}",
        refresh_token,
        ex=int(refresh_token_expires.total_seconds())
    )
    
    # 更新最后登录时间和IP
    await UserService.update_login_info(db, user.id, login_type="password")
    
    # 记录登录成功日志
    await LoginLogService.record_login(
        db=db,
        username=user.username,
        user_id=user.id,
        status=1,
        login_ip=client_info["login_ip"],
        user_agent=client_info["user_agent"],
        browser_type=client_info["browser_type"],
        os_type=client_info["os_type"],
        device_type=client_info["device_type"],
        login_type="password",
    )
    
    return TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        tokenType="bearer",
        expireTime=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login/oauth2", response_model=TokenResponse, summary="用户登录(OAuth2)", include_in_schema=True)
async def login_oauth2(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录（OAuth2表单格式，供Swagger使用）
    
    - **username**: 用户名
    - **password**: 密码
    
    返回access_token和refresh_token（标准OAuth2格式）
    """
    # 获取客户端信息
    client_info = get_client_info(request)
    
    # 验证用户
    user = await UserService.authenticate(db, form_data.username, form_data.password)
    if not user:
        # 记录登录失败日志
        await LoginLogService.record_login(
            db=db,
            username=form_data.username,
            status=0,
            login_ip=client_info["login_ip"],
            failure_reason=2,
            failure_message="用户名或密码错误",
            user_agent=client_info["user_agent"],
            browser_type=client_info["browser_type"],
            os_type=client_info["os_type"],
            device_type=client_info["device_type"],
            login_type="password",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户状态
    if not user.is_active:
        await LoginLogService.record_login(
            db=db,
            username=form_data.username,
            user_id=user.id,
            status=0,
            login_ip=client_info["login_ip"],
            failure_reason=3,
            failure_message="用户已被禁用",
            user_agent=client_info["user_agent"],
            browser_type=client_info["browser_type"],
            os_type=client_info["os_type"],
            device_type=client_info["device_type"],
            login_type="password",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    if user.user_status != 1:
        status_msg = {0: "用户已禁用", 2: "用户已锁定"}.get(user.user_status, "用户状态异常")
        failure_reason = 3 if user.user_status == 0 else 4
        await LoginLogService.record_login(
            db=db,
            username=form_data.username,
            user_id=user.id,
            status=0,
            login_ip=client_info["login_ip"],
            failure_reason=failure_reason,
            failure_message=status_msg,
            user_agent=client_info["user_agent"],
            browser_type=client_info["browser_type"],
            os_type=client_info["os_type"],
            device_type=client_info["device_type"],
            login_type="password",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=status_msg
        )
    
    # 生成token（包含角色信息）
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    token_data = {
        "sub": user.id,
        "username": user.username,
        "role_id": user.role_id,
        "is_superuser": user.is_superuser,
    }
    access_token = create_access_token(token_data, access_token_expires)
    refresh_token = create_refresh_token(token_data, refresh_token_expires)
    
    # 将refresh token存入Redis
    redis = await RedisClient.get_client()
    await redis.set(
        f"{REFRESH_TOKEN_PREFIX}{user.id}",
        refresh_token,
        ex=int(refresh_token_expires.total_seconds())
    )
    
    # 更新最后登录时间
    await UserService.update_login_info(db, user.id, login_type="password")
    
    # 记录登录成功日志
    await LoginLogService.record_login(
        db=db,
        username=user.username,
        user_id=user.id,
        status=1,
        login_ip=client_info["login_ip"],
        user_agent=client_info["user_agent"],
        browser_type=client_info["browser_type"],
        os_type=client_info["os_type"],
        device_type=client_info["device_type"],
        login_type="password",
    )
    
    return TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        tokenType="bearer",
        expireTime=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh_token", response_model=TokenResponse, summary="刷新Token")
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    使用refresh_token获取新的access_token
    
    - **refresh_token**: 刷新令牌
    
    返回新的access_token和refresh_token
    """
    # 从request的header中获取refresh_token
    data = RefreshTokenRequest(refresh_token=request.headers.get("Authorization").split(" ")[1])

    # 验证refresh token
    payload = verify_refresh_token(data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查refresh token是否在Redis中（防止已登出的token被使用）
    redis = await RedisClient.get_client()
    stored_token = await redis.get(f"{REFRESH_TOKEN_PREFIX}{user_id}")
    if not stored_token or stored_token != data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已失效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否存在且有效
    user = await UserService.get_by_id(db, user_id)
    if not user or not user.is_active or user.user_status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 生成新的token（包含角色信息）
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    token_data = {
        "sub": user.id,
        "username": user.username,
        "role_id": user.role_id,
        "is_superuser": user.is_superuser,
    }
    new_access_token = create_access_token(token_data, access_token_expires)
    new_refresh_token = create_refresh_token(token_data, refresh_token_expires)
    
    # 更新Redis中的refresh token
    redis = await RedisClient.get_client()
    await redis.set(
        f"{REFRESH_TOKEN_PREFIX}{user.id}",
        new_refresh_token,
        ex=int(refresh_token_expires.total_seconds())
    )
    
    return TokenResponse(
        accessToken=new_access_token,
        refreshToken=new_refresh_token,
        tokenType="bearer",
        expireTime=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/logout", response_model=ResponseModel, summary="用户登出")
async def logout(request: Request):
    """
    用户登出
    
    需要携带有效的access_token
    """
    # 删除Redis中的refresh token

    user_id = request.state.user_id
    redis = await RedisClient.get_client()
    await redis.delete(f"{REFRESH_TOKEN_PREFIX}{user_id}")
    
    return ResponseModel(message="登出成功")


@router.get("/userinfo", response_model=LoginUserInfo, summary="获取当前用户信息")
async def get_me(
    current_user = Depends(get_current_user)
):
    """
    获取当前登录用户信息
    
    需要携带有效的access_token
    """
    return LoginUserInfo(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        email=current_user.email,
        mobile=current_user.mobile,
        avatar=current_user.avatar,
        is_superuser=current_user.is_superuser,
        dept_id=current_user.dept_id,
        user_type=current_user.user_type or 1,
        user_status=current_user.user_status or 1,
    )


@router.get("/menus", response_model=dict, summary="获取当前用户的菜单")
async def get_user_menus(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户有权访问的菜单树
    
    - 超级管理员返回所有菜单
    - 普通用户返回角色关联的菜单
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from core.menu.model import Menu
    from core.role.model import Role
    
    # 超级管理员获取所有菜单
    if current_user.is_superuser:
        result = await db.execute(
            select(Menu).where(
                Menu.is_deleted == False,  # noqa: E712
                Menu.status == True  # noqa: E712
            ).order_by(Menu.sort, Menu.sys_create_datetime)
        )
        all_menus = list(result.scalars().all())
    else:
        # 普通用户获取角色关联的菜单
        if not current_user.role_id:
            return {"menus": [], "home": None}
        
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.menus))
            .where(
                Role.id == current_user.role_id,
                Role.status == True,  # noqa: E712
                Role.is_deleted == False  # noqa: E712
            )
        )
        role = result.scalar_one_or_none()
        
        if not role or not role.menus:
            return {"menus": [], "home": None}
        
        all_menus = [m for m in role.menus if m.status and not m.is_deleted]
    
    # 构建菜单树
    menu_map = {}
    root_menus = []
    
    for menu in all_menus:
        menu_node = {
            "id": menu.id,
            "name": menu.name,
            "title": menu.title,
            "path": menu.path,
            "component": menu.component,
            "icon": menu.icon,
            "menu_type": menu.menu_type,
            "parent_id": menu.parent_id,
            "sort": menu.sort,
            "is_hidden": menu.is_hidden,
            "is_cache": menu.is_cache,
            "is_affix": menu.is_affix,
            "redirect": menu.redirect,
            "children": [],
        }
        menu_map[menu.id] = menu_node
    
    # 建立父子关系
    for menu in all_menus:
        if menu.parent_id and menu.parent_id in menu_map:
            menu_map[menu.parent_id]["children"].append(menu_map[menu.id])
        else:
            root_menus.append(menu_map[menu.id])
    
    # 按sort排序
    def sort_menus(menus):
        menus.sort(key=lambda x: x.get("sort", 0))
        for menu in menus:
            if menu.get("children"):
                sort_menus(menu["children"])
    
    sort_menus(root_menus)
    
    # 获取首页
    home = None
    for menu in all_menus:
        if menu.is_affix and menu.menu_type == 1:
            home = menu.path
            break
    
    return {"menus": root_menus, "home": home}


@router.get("/permissions", response_model=dict, summary="获取当前用户的权限")
async def get_user_permissions(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的权限码列表
    
    - 超级管理员返回 ["*"]（代表所有权限）
    - 普通用户返回角色关联的权限码列表
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from core.role.model import Role
    
    # 超级管理员拥有所有权限
    if current_user.is_superuser:
        return {"permissions": ["*"], "is_superuser": True}
    
    # 普通用户获取角色关联的权限
    if not current_user.role_id:
        return {"permissions": [], "is_superuser": False}
    
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(
            Role.id == current_user.role_id,
            Role.status == True,  # noqa: E712
            Role.is_deleted == False  # noqa: E712
        )
    )
    role = result.scalar_one_or_none()
    
    if not role or not role.permissions:
        return {"permissions": [], "is_superuser": False}
    
    permission_codes = [p.code for p in role.permissions if p.is_active]
    
    return {"permissions": permission_codes, "is_superuser": False}
