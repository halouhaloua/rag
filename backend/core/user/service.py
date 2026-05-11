#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: service.py
@Desc: User Service - 用户服务层
"""
"""
User Service - 用户服务层
"""
from io import BytesIO
from typing import Tuple, Dict, Any, Optional, List
from datetime import datetime

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_service import BaseService
from core.user.model import User
from core.user.schema import UserCreate, UserUpdate

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService(BaseService[User, UserCreate, UserUpdate]):
    """
    用户服务层
    继承BaseService，自动获得增删改查功能
    """
    
    model = User
    
    # Excel导入导出配置
    excel_columns = {
        "username": "用户名",
        "name": "姓名",
        "email": "邮箱",
        "mobile": "手机号",
        "gender": "性别",
        "user_type": "用户类型",
        "user_status": "用户状态",
    }
    excel_sheet_name = "用户列表"
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """加密密码"""
        return pwd_context.hash(password)
    
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @classmethod
    def _export_converter(cls, item: Any) -> Dict[str, Any]:
        """导出数据转换器"""
        return {
            "username": item.username,
            "name": item.name or "",
            "email": item.email or "",
            "mobile": item.mobile or "",
            "gender": item.get_gender_display(),
            "user_type": item.get_user_type_display(),
            "user_status": item.get_user_status_display(),
        }
    
    @classmethod
    def _import_processor(cls, row: Dict[str, Any]) -> Optional[User]:
        """导入数据处理器"""
        username = row.get("username")
        if not username:
            return None
        
        # 性别映射
        gender_map = {"未知": 0, "男": 1, "女": 2}
        gender_str = row.get("gender", "未知")
        gender = gender_map.get(gender_str, 0)
        
        # 用户类型映射
        type_map = {"系统用户": 0, "普通用户": 1, "外部用户": 2}
        type_str = row.get("user_type", "普通用户")
        user_type = type_map.get(type_str, 1)
        
        # 用户状态映射
        status_map = {"禁用": 0, "正常": 1, "锁定": 2}
        status_str = row.get("user_status", "正常")
        user_status = status_map.get(status_str, 1)
        
        return User(
            username=str(username),
            password=cls.hash_password("123456"),  # 默认密码
            name=str(row.get("name") or "") or None,
            email=str(row.get("email") or "") or None,
            mobile=str(row.get("mobile") or "") or None,
            gender=gender,
            user_type=user_type,
            user_status=user_status,
        )
    
    @classmethod
    async def export_to_excel(
        cls,
        db: AsyncSession,
        data_converter: Any = None
    ) -> BytesIO:
        """导出到Excel"""
        return await super().export_to_excel(db, cls._export_converter)
    
    @classmethod
    async def import_from_excel(
        cls,
        db: AsyncSession,
        file_content: bytes,
        row_processor: Any = None
    ) -> Tuple[int, int]:
        """从Excel导入"""
        return await super().import_from_excel(db, file_content, cls._import_processor)
    
    @classmethod
    async def create(cls, db: AsyncSession, data: UserCreate) -> User:
        """
        创建用户，自动加密密码
        """
        user_data = data.model_dump()
        # 加密密码
        user_data["password"] = cls.hash_password('123456')
        
        db_obj = User(**user_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @classmethod
    async def get_by_username(cls, db: AsyncSession, username: str) -> Optional[User]:
        """
        根据用户名获取用户
        """
        result = await db.execute(
            select(User).where(
                User.username == username,
                User.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_email(cls, db: AsyncSession, email: str) -> Optional[User]:
        """
        根据邮箱获取用户
        """
        result = await db.execute(
            select(User).where(
                User.email == email,
                User.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_mobile(cls, db: AsyncSession, mobile: str) -> Optional[User]:
        """
        根据手机号获取用户
        """
        result = await db.execute(
            select(User).where(
                User.mobile == mobile,
                User.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def authenticate(cls, db: AsyncSession, username: str, password: str) -> Optional[User]:
        """
        用户认证
        
        :return: 认证成功返回用户，失败返回None
        """
        user = await cls.get_by_username(db, username)
        if not user:
            return None
        if not cls.verify_password(password, user.password):
            return None
        if not user.is_active_user():
            return None
        return user
    
    @classmethod
    async def change_password(
        cls,
        db: AsyncSession,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        修改密码
        
        :return: (是否成功, 消息)
        """
        user = await cls.get_by_id(db, user_id)
        if not user:
            return False, "用户不存在"
        
        if not cls.verify_password(old_password, user.password):
            return False, "原密码错误"
        
        user.password = cls.hash_password(new_password)
        await db.commit()
        return True, "密码修改成功"
    
    @classmethod
    async def reset_password(
        cls,
        db: AsyncSession,
        user_id: str,
        new_password: str
    ) -> bool:
        """
        重置密码（管理员操作）
        """
        user = await cls.get_by_id(db, user_id)
        if not user:
            return False
        
        user.password = cls.hash_password(new_password)
        await db.commit()
        return True
    
    @classmethod
    async def update_last_login(
        cls,
        db: AsyncSession,
        user_id: str,
        ip: Optional[str] = None,
        login_type: Optional[str] = None
    ) -> bool:
        """
        更新最后登录信息
        """
        user = await cls.get_by_id(db, user_id)
        if not user:
            return False
        
        user.last_login = datetime.now()
        if ip:
            user.last_login_ip = ip
        if login_type:
            user.last_login_type = login_type
        
        await db.commit()
        return True
    
    @classmethod
    async def update_login_info(
        cls,
        db: AsyncSession,
        user_id: str,
        ip: Optional[str] = None,
        login_type: Optional[str] = None
    ) -> bool:
        """
        更新登录信息（update_last_login的别名）
        """
        return await cls.update_last_login(db, user_id, ip, login_type)
    
    @classmethod
    async def batch_update_status(
        cls,
        db: AsyncSession,
        ids: List[str],
        user_status: int
    ) -> int:
        """
        批量更新用户状态
        
        :return: 更新的记录数
        """
        count = 0
        for user_id in ids:
            user = await cls.get_by_id(db, user_id)
            if user and not user.is_superuser:  # 超级管理员不能被修改状态
                user.user_status = user_status
                count += 1
        
        if count > 0:
            await db.commit()
        
        return count
    
    # @classmethod
    # async def batch_delete(
    #     cls,
    #     db: AsyncSession,
    #     ids: List[str],
    #     hard: bool = False
    # ) -> Tuple[int, List[str]]:
    #     """
    #     批量删除用户
    #
    #     :return: (删除成功数, 删除失败的ID列表)
    #     """
    #     success_count = 0
    #     failed_ids = []
    #
    #     for user_id in ids:
    #         user = await cls.get_by_id(db, user_id)
    #         if user:
    #             if user.can_delete():
    #                 if await cls.delete(db, user_id, hard=hard):
    #                     success_count += 1
    #                 else:
    #                     failed_ids.append(user_id)
    #             else:
    #                 failed_ids.append(user_id)
    #         else:
    #             failed_ids.append(user_id)
    #
    #     return success_count, failed_ids
    
    @classmethod
    async def get_subordinates(cls, db: AsyncSession, user_id: str) -> List[User]:
        """
        获取下属用户列表
        """
        result = await db.execute(
            select(User).where(
                User.manager_id == user_id,
                User.is_deleted == False  # noqa: E712
            )
        )
        return list(result.scalars().all())
    
    @classmethod
    async def get_by_dept(cls, db: AsyncSession, dept_id: str) -> List[User]:
        """
        获取部门下的用户列表
        """
        result = await db.execute(
            select(User).where(
                User.dept_id == dept_id,
                User.is_deleted == False  # noqa: E712
            )
        )
        return list(result.scalars().all())
