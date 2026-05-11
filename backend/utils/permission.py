#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: permission.py
@Desc: Permission Utils - 基于API路径的动态权限鉴权 - 
"""
"""
Permission Utils - 基于API路径的动态权限鉴权

工作原理：
1. 用户访问某个API时，根据请求的路径和方法，查找Permission表中是否有对应的权限记录
2. 如果有权限记录，检查用户的角色是否关联了该权限
3. 如果用户角色有该权限，则放行；否则返回403
4. 如果Permission表中没有该API的权限记录，则默认放行（未配置权限的API不做限制）
"""
import re
from typing import List, Optional, Dict, Any, Set
from functools import lru_cache

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


# HTTP方法映射（与Permission模型中的定义一致）
HTTP_METHOD_MAP = {
    'GET': 0,
    'POST': 1,
    'PUT': 2,
    'DELETE': 3,
    'PATCH': 4,
    'ALL': 5,
}


class APIPermissionChecker:
    """
    基于API路径的动态权限检查器
    
    在AuthMiddleware中调用，根据请求的API路径和方法检查用户是否有权限
    """
    
    def __init__(self):
        # 缓存：存储API路径到权限的映射
        # 格式: {(api_path, http_method): permission_id}
        self._permission_cache: Dict[tuple, str] = {}
        self._cache_loaded = False
    
    async def load_permissions_cache(self, db: AsyncSession):
        """
        加载所有API权限到缓存
        
        建议在应用启动时调用，或者定期刷新
        """
        from core.permission.model import Permission
        
        result = await db.execute(
            select(Permission).where(
                Permission.is_active == True,  # noqa: E712
                Permission.is_deleted == False,  # noqa: E712
                Permission.permission_type == 1,  # 只缓存API权限
                Permission.api_path.isnot(None)
            )
        )
        permissions = result.scalars().all()
        
        self._permission_cache.clear()
        for perm in permissions:
            if perm.api_path:
                # 存储权限ID，key为(路径, 方法)
                self._permission_cache[(perm.api_path, perm.http_method)] = perm.id
                # 如果是ALL方法，也存储到各个具体方法
                if perm.http_method == 5:  # ALL
                    for method_code in [0, 1, 2, 3, 4]:
                        key = (perm.api_path, method_code)
                        if key not in self._permission_cache:
                            self._permission_cache[key] = perm.id
        
        self._cache_loaded = True
    
    def clear_cache(self):
        """清除权限缓存"""
        self._permission_cache.clear()
        self._cache_loaded = False
    
    def _match_path(self, request_path: str, permission_path: str) -> bool:
        """
        匹配请求路径和权限路径
        
        支持路径参数，如 /api/user/{id} 匹配 /api/user/123
        """
        # 将权限路径中的{xxx}替换为正则表达式
        pattern = re.sub(r'\{[^}]+\}', r'[^/]+', permission_path)
        pattern = f'^{pattern}$'
        return bool(re.match(pattern, request_path))
    
    def find_permission_id(self, request_path: str, http_method: str) -> Optional[str]:
        """
        根据请求路径和方法查找对应的权限ID
        
        :param request_path: 请求路径，如 /api/core/user
        :param http_method: HTTP方法，如 GET, POST
        :return: 权限ID，如果没有找到则返回None
        """
        method_code = HTTP_METHOD_MAP.get(http_method.upper(), 0)
        
        # 1. 精确匹配
        key = (request_path, method_code)
        if key in self._permission_cache:
            return self._permission_cache[key]
        
        # 2. 尝试匹配ALL方法
        key_all = (request_path, 5)  # ALL
        if key_all in self._permission_cache:
            return self._permission_cache[key_all]
        
        # 3. 路径参数匹配
        for (perm_path, perm_method), perm_id in self._permission_cache.items():
            if perm_method in (method_code, 5):  # 匹配具体方法或ALL
                if '{' in perm_path and self._match_path(request_path, perm_path):
                    return perm_id
        
        return None
    
    async def check_permission(
        self,
        db: AsyncSession,
        user_id: str,
        role_id: Optional[str],
        is_superuser: bool,
        request_path: str,
        http_method: str,
    ) -> tuple[bool, str]:
        """
        检查用户是否有访问指定API的权限
        
        :param db: 数据库会话
        :param user_id: 用户ID
        :param role_id: 角色ID
        :param is_superuser: 是否超级管理员
        :param request_path: 请求路径
        :param http_method: HTTP方法
        :return: (是否有权限, 错误信息)
        """
        # 超级管理员跳过权限检查
        if is_superuser:
            return True, ""
        
        # 确保缓存已加载
        if not self._cache_loaded:
            await self.load_permissions_cache(db)
        
        # 查找该API对应的权限
        permission_id = self.find_permission_id(request_path, http_method)
        
        # 如果该API没有配置权限，默认放行
        if not permission_id:
            return True, ""
        
        # 用户没有角色，无权限
        if not role_id:
            return False, "用户未分配角色，无权访问此接口"
        
        # 检查用户角色是否有该权限
        has_permission = await self._check_role_has_permission(db, role_id, permission_id)
        
        if has_permission:
            return True, ""
        else:
            return False, "权限不足，无权访问此接口"
    
    async def _check_role_has_permission(
        self,
        db: AsyncSession,
        role_id: str,
        permission_id: str
    ) -> bool:
        """
        检查角色是否有指定权限
        """
        from core.role.model import Role
        
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(
                Role.id == role_id,
                Role.status == True,  # noqa: E712
                Role.is_deleted == False  # noqa: E712
            )
        )
        role = result.scalar_one_or_none()
        
        if not role or not role.permissions:
            return False
        
        # 检查角色的权限列表中是否包含该权限
        for perm in role.permissions:
            if perm.id == permission_id and perm.is_active:
                return True
        
        return False


# 全局权限检查器实例
api_permission_checker = APIPermissionChecker()


async def check_api_permission(
    db: AsyncSession,
    user_id: str,
    role_id: Optional[str],
    is_superuser: bool,
    request_path: str,
    http_method: str,
) -> tuple[bool, str]:
    """
    检查API权限的便捷函数
    
    :return: (是否有权限, 错误信息)
    """
    return await api_permission_checker.check_permission(
        db, user_id, role_id, is_superuser, request_path, http_method
    )


async def refresh_permission_cache(db: AsyncSession):
    """
    刷新权限缓存
    
    当权限数据变更时调用此函数
    """
    await api_permission_checker.load_permissions_cache(db)


def clear_permission_cache():
    """
    清除权限缓存
    """
    api_permission_checker.clear_cache()


async def get_user_api_permissions(
    db: AsyncSession,
    role_id: Optional[str],
    is_superuser: bool,
) -> Set[str]:
    """
    获取用户有权访问的所有API路径
    
    :return: API路径集合
    """
    if is_superuser:
        return {"*"}  # 超级管理员有所有权限
    
    if not role_id:
        return set()
    
    from core.role.model import Role
    
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(
            Role.id == role_id,
            Role.status == True,  # noqa: E712
            Role.is_deleted == False  # noqa: E712
        )
    )
    role = result.scalar_one_or_none()
    
    if not role or not role.permissions:
        return set()
    
    # 返回所有API权限的路径
    return {
        perm.api_path
        for perm in role.permissions
        if perm.is_active and perm.permission_type == 1 and perm.api_path
    }


async def get_user_permission_codes(
    db: AsyncSession,
    role_id: Optional[str],
    is_superuser: bool,
) -> Set[str]:
    """
    获取用户的所有权限码（用于前端按钮权限控制）
    
    :return: 权限码集合
    """
    if is_superuser:
        return {"*"}  # 超级管理员有所有权限
    
    if not role_id:
        return set()
    
    from core.role.model import Role
    
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(
            Role.id == role_id,
            Role.status == True,  # noqa: E712
            Role.is_deleted == False  # noqa: E712
        )
    )
    role = result.scalar_one_or_none()
    
    if not role or not role.permissions:
        return set()
    
    return {perm.code for perm in role.permissions if perm.is_active}


async def get_api_data_scope(
    db: AsyncSession,
    role_id: Optional[str],
    is_superuser: bool,
    request_path: str,
    http_method: str,
) -> int:
    """
    获取用户对指定API的数据权限范围
    
    :param db: 数据库会话
    :param role_id: 角色ID
    :param is_superuser: 是否超级管理员
    :param request_path: 请求路径
    :param http_method: HTTP方法
    :return: 数据权限范围（0-全部, 1-仅本人, 2-本部门, 3-本部门及下级, 4-自定义）
    """
    # 超级管理员默认全部数据
    if is_superuser:
        return 0  # 全部数据
    
    if not role_id:
        return 1  # 无角色默认仅本人
    
    # 确保缓存已加载
    if not api_permission_checker._cache_loaded:
        await api_permission_checker.load_permissions_cache(db)
    
    # 查找该API对应的权限
    permission_id = api_permission_checker.find_permission_id(request_path, http_method)
    
    # 如果该API没有配置权限，默认全部数据
    if not permission_id:
        return 0
    
    # 获取权限的data_scope
    from core.permission.model import Permission
    
    result = await db.execute(
        select(Permission).where(Permission.id == permission_id)
    )
    permission = result.scalar_one_or_none()
    
    if not permission:
        return 0
    
    return permission.data_scope


async def apply_data_scope_filter(
    db: AsyncSession,
    role_id: Optional[str],
    is_superuser: bool,
    user_id: str,
    user_dept_id: Optional[str],
    request_path: str,
    http_method: str,
) -> Dict[str, Any]:
    """
    根据数据权限范围返回过滤条件
    
    :return: 包含过滤条件的字典
        - scope: 数据权限范围值
        - filter_type: 过滤类型 ('all', 'self', 'dept', 'dept_and_children', 'custom')
        - user_id: 当scope=1时，用于过滤仅本人数据
        - dept_id: 当scope=2时，用于过滤本部门数据
        - dept_ids: 当scope=3或4时，用于过滤部门列表数据
    """
    data_scope = await get_api_data_scope(db, role_id, is_superuser, request_path, http_method)
    
    result = {
        'scope': data_scope,
        'filter_type': 'all',
        'user_id': None,
        'dept_id': None,
        'dept_ids': None,
    }
    
    # 0: 全部数据
    if data_scope == 0:
        result['filter_type'] = 'all'
        return result
    
    # 1: 仅本人数据
    if data_scope == 1:
        result['filter_type'] = 'self'
        result['user_id'] = user_id
        return result
    
    # 2: 本部门数据
    if data_scope == 2:
        result['filter_type'] = 'dept'
        result['dept_id'] = user_dept_id
        return result
    
    # 3: 本部门及下级部门数据
    if data_scope == 3:
        result['filter_type'] = 'dept_and_children'
        if user_dept_id:
            from core.dept.service import DeptService
            descendants = await DeptService.get_descendants(db, user_dept_id)
            dept_ids = [user_dept_id] + [d.id for d in descendants]
            result['dept_ids'] = dept_ids
        else:
            result['dept_ids'] = []
        return result
    
    # 4: 自定义数据权限（基于角色关联的部门）
    if data_scope == 4:
        result['filter_type'] = 'custom'
        if role_id:
            from core.role.model import Role
            role_result = await db.execute(
                select(Role)
                .options(selectinload(Role.depts))
                .where(Role.id == role_id)
            )
            role = role_result.scalar_one_or_none()
            if role and role.depts:
                result['dept_ids'] = [d.id for d in role.depts]
            else:
                result['dept_ids'] = []
        else:
            result['dept_ids'] = []
        return result
    
    return result


# 数据权限范围常量
DATA_SCOPE_ALL = 0          # 全部数据
DATA_SCOPE_SELF = 1         # 仅本人数据
DATA_SCOPE_DEPT = 2         # 本部门数据
DATA_SCOPE_DEPT_TREE = 3    # 本部门及下级部门数据
DATA_SCOPE_CUSTOM = 4       # 自定义数据
