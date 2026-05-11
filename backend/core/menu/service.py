#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: service.py
@Desc: Menu Service - 菜单服务层
"""
"""
Menu Service - 菜单服务层
"""
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_service import BaseService
from utils.redis import CacheManager
from core.menu.model import Menu
from core.menu.schema import MenuCreate, MenuUpdate

# 菜单缓存管理器
menu_cache = CacheManager(prefix="menu:")

# 缓存key
MENU_TREE_CACHE_KEY = "tree"
USER_ROUTE_CACHE_PREFIX = "user_route:"


class MenuService(BaseService[Menu, MenuCreate, MenuUpdate]):
    """
    菜单服务层
    继承BaseService，自动获得增删改查功能
    """
    
    model = Menu
    
    @classmethod
    async def get_by_name(cls, db: AsyncSession, name: str) -> Optional[Menu]:
        """根据菜单名称获取菜单"""
        result = await db.execute(
            select(Menu).where(
                Menu.name == name,
                Menu.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_path(cls, db: AsyncSession, path: str) -> Optional[Menu]:
        """根据路由路径获取菜单"""
        result = await db.execute(
            select(Menu).where(
                Menu.path == path,
                Menu.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def check_name_exists(
        cls,
        db: AsyncSession,
        name: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """检查菜单名称是否存在"""
        query = select(Menu).where(
            Menu.name == name,
            Menu.is_deleted == False  # noqa: E712
        )
        if exclude_id:
            query = query.where(Menu.id != exclude_id)
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    @classmethod
    async def check_path_exists(
        cls,
        db: AsyncSession,
        path: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """检查路由路径是否存在"""
        query = select(Menu).where(
            Menu.path == path,
            Menu.is_deleted == False  # noqa: E712
        )
        if exclude_id:
            query = query.where(Menu.id != exclude_id)
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    @classmethod
    async def get_children(cls, db: AsyncSession, parent_id: Optional[str]) -> List[Menu]:
        """获取直接子菜单"""
        if parent_id:
            query = select(Menu).where(
                Menu.parent_id == parent_id,
                Menu.is_deleted == False  # noqa: E712
            ).order_by(Menu.order)
        else:
            query = select(Menu).where(
                Menu.parent_id.is_(None),
                Menu.is_deleted == False  # noqa: E712
            ).order_by(Menu.order)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def get_child_count(cls, db: AsyncSession, menu_id: str) -> int:
        """获取直接子菜单数量"""
        result = await db.execute(
            select(func.count(Menu.id)).where(
                Menu.parent_id == menu_id,
                Menu.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar() or 0
    
    @classmethod
    async def get_level(cls, db: AsyncSession, menu: Menu) -> int:
        """计算菜单层级"""
        level = 0
        current = menu
        while current.parent_id:
            level += 1
            parent = await cls.get_by_id(db, current.parent_id)
            if not parent:
                break
            current = parent
        return level
    
    @classmethod
    async def get_ancestors(cls, db: AsyncSession, menu: Menu) -> List[Menu]:
        """获取所有祖先菜单"""
        ancestors = []
        current = menu
        while current.parent_id:
            parent = await cls.get_by_id(db, current.parent_id)
            if not parent:
                break
            ancestors.append(parent)
            current = parent
        return ancestors
    
    @classmethod
    async def get_descendants(cls, db: AsyncSession, menu_id: str) -> List[Menu]:
        """获取所有后代菜单"""
        descendants = []
        
        async def collect_children(parent_id: str):
            children = await cls.get_children(db, parent_id)
            for child in children:
                descendants.append(child)
                await collect_children(child.id)
        
        await collect_children(menu_id)
        return descendants
    
    @classmethod
    async def can_delete(cls, db: AsyncSession, menu_id: str) -> bool:
        """判断是否可以删除（没有子菜单）"""
        child_count = await cls.get_child_count(db, menu_id)
        return child_count == 0
    
    @classmethod
    async def get_all_menus(cls, db: AsyncSession) -> List[Menu]:
        """获取所有菜单"""
        result = await db.execute(
            select(Menu).where(
                Menu.is_deleted == False  # noqa: E712
            ).order_by(Menu.order)
        )
        return list(result.scalars().all())
    
    @classmethod
    async def build_tree(cls, db: AsyncSession) -> List[Dict[str, Any]]:
        """构建菜单树"""
        menus = await cls.get_all_menus(db)
        
        # 构建菜单字典
        menu_dict = {}
        for menu in menus:
            child_count = await cls.get_child_count(db, menu.id)
            level = await cls.get_level(db, menu)
            menu_dict[menu.id] = {
                "id": menu.id,
                "parent_id": menu.parent_id,
                "component": menu.component,
                "name": menu.name,
                "title": menu.title,
                "path": menu.path,
                "type": menu.type,
                "icon": menu.icon,
                "order": menu.order,
                "level": level,
                "childCount": child_count,
                "children": []
            }
        
        # 构建树形结构
        tree = []
        for menu_id, menu_data in menu_dict.items():
            parent_id = menu_data["parent_id"]
            if parent_id is None:
                tree.append(menu_data)
            elif parent_id in menu_dict:
                menu_dict[parent_id]["children"].append(menu_data)
        
        # 递归排序
        def sort_children(nodes):
            nodes.sort(key=lambda x: x["order"])
            for node in nodes:
                if node["children"]:
                    sort_children(node["children"])
        
        sort_children(tree)
        return tree
    
    @classmethod
    async def build_route_tree(cls, menus: List[Menu]) -> List[Dict[str, Any]]:
        """构建前端路由树"""
        # 构建菜单字典
        menu_dict = {}
        for menu in menus:
            meta = {
                "title": menu.title or menu.name,
                "icon": menu.icon,
                "activeIcon": menu.activeIcon,
                "hideInMenu": menu.hideInMenu,
                "hideChildrenInMenu": menu.hideChildrenInMenu,
                "hideInBreadcrumb": menu.hideInBreadcrumb,
                "hideInTab": menu.hideInTab,
                "affixTab": menu.affixTab,
                "affixTabOrder": menu.affixTabOrder,
                "keepAlive": menu.keepAlive,
                "maxNumOfOpenTab": menu.maxNumOfOpenTab,
                "noBasicLayout": menu.noBasicLayout,
                "badge": menu.badge,
                "badgeType": menu.badgeType,
                "badgeVariants": menu.badgeVariants,
                "link": menu.link,
                "iframeSrc": menu.iframeSrc,
                "openInNewWindow": menu.openInNewWindow,
                "activePath": menu.activePath,
                "authCode": menu.authCode,
            }
            # 移除None值
            meta = {k: v for k, v in meta.items() if v is not None}

            menu_dict[menu.id] = {
                "name": menu.name,
                "path": menu.path,
                "component": menu.component,
                "redirect": menu.redirect,
                "meta": meta,
                "children": [],
                "_parent_id": menu.parent_id,
                "_order": menu.order,
            }

        # 构建树形结构
        tree = []
        for menu_id, menu_data in menu_dict.items():
            parent_id = menu_data.pop("_parent_id")
            if parent_id is None:
                tree.append(menu_data)
            elif parent_id in menu_dict:
                menu_dict[parent_id]["children"].append(menu_data)

        # 递归排序并清理
        def sort_and_clean(nodes):
            nodes.sort(key=lambda x: x.pop("_order", 0))
            for node in nodes:
                if node["children"]:
                    sort_and_clean(node["children"])
                else:
                    node.pop("children", None)

        sort_and_clean(tree)
        return tree
    
    @classmethod
    async def get_menu_tree_cached(cls, db: AsyncSession) -> List[Dict[str, Any]]:
        """获取菜单树（带缓存）"""
        # 尝试从缓存获取
        cached = await menu_cache.get(MENU_TREE_CACHE_KEY)
        if cached:
            return cached
        
        # 从数据库构建
        tree = await cls.build_tree(db)
        
        # 缓存结果（1小时）
        await menu_cache.set(MENU_TREE_CACHE_KEY, tree, expire=3600)
        
        return tree
    
    @classmethod
    async def get_user_route_tree(
        cls,
        db: AsyncSession,
        user_id: str,
        is_superuser: bool = False,
        role_menu_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """获取用户路由树"""
        cache_key = f"{USER_ROUTE_CACHE_PREFIX}{user_id}"
        
        # 尝试从缓存获取
        cached = await menu_cache.get(cache_key)
        if cached:
            return cached
        
        # 获取菜单
        if is_superuser:
            menus = await cls.get_all_menus(db)
        elif role_menu_ids:
            result = await db.execute(
                select(Menu).where(
                    Menu.id.in_(role_menu_ids),
                    Menu.is_deleted == False  # noqa: E712
                ).order_by(Menu.order)
            )
            menus = list(result.scalars().all())
        else:
            menus = []
        
        # 构建路由树
        tree = await cls.build_route_tree(menus)
        
        # 缓存结果（5分钟，权限可能变更）
        await menu_cache.set(cache_key, tree, expire=300)
        
        return tree
    
    @classmethod
    async def invalidate_cache(cls):
        """清除菜单缓存"""
        await menu_cache.delete(MENU_TREE_CACHE_KEY)
        await menu_cache.delete_pattern(f"{USER_ROUTE_CACHE_PREFIX}*")
    
    @classmethod
    async def move_menu(
        cls,
        db: AsyncSession,
        menu_id: str,
        new_parent_id: Optional[str]
    ) -> Tuple[bool, str]:
        """
        移动菜单到新的父菜单下
        
        :return: (是否成功, 消息)
        """
        menu = await cls.get_by_id(db, menu_id)
        if not menu:
            return False, "菜单不存在"
        
        # 检查新父菜单
        if new_parent_id:
            if new_parent_id == menu_id:
                return False, "不能将自己设置为父菜单"
            
            new_parent = await cls.get_by_id(db, new_parent_id)
            if not new_parent:
                return False, "父菜单不存在"
            
            # 检查是否会形成循环引用
            ancestors = await cls.get_ancestors(db, new_parent)
            ancestor_ids = [a.id for a in ancestors]
            if menu.id in ancestor_ids or menu.id == new_parent.id:
                return False, "不能移动到自己或子菜单下"
        
        menu.parent_id = new_parent_id
        await db.commit()
        await cls.invalidate_cache()
        
        return True, "移动成功"
    
    @classmethod
    async def get_menu_stats(cls, db: AsyncSession) -> Dict[str, Any]:
        """获取菜单统计信息"""
        # 总数
        total_result = await db.execute(
            select(func.count(Menu.id)).where(Menu.is_deleted == False)  # noqa: E712
        )
        total_count = total_result.scalar() or 0
        
        # 按类型统计
        type_stats = {}
        type_choices = [
            ('catalog', '目录'),
            ('menu', '菜单'),
            ('external', '外部链接'),
            ('online_form', '在线表单'),
            ('online_page', '在线页面'),
        ]
        for type_code, type_name in type_choices:
            count_result = await db.execute(
                select(func.count(Menu.id)).where(
                    Menu.type == type_code,
                    Menu.is_deleted == False  # noqa: E712
                )
            )
            type_stats[type_name] = count_result.scalar() or 0
        
        # 计算最大层级
        max_level = 0
        menus = await cls.get_all_menus(db)
        for menu in menus:
            level = await cls.get_level(db, menu)
            if level > max_level:
                max_level = level
        
        return {
            "totalCount": total_count,
            "typeStats": type_stats,
            "maxLevel": max_level,
        }
