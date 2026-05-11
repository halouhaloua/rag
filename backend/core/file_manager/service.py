#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: service.py
@Desc: 文件管理服务
"""
"""
文件管理服务
"""
import mimetypes
import os
from typing import Optional, List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_service import BaseService
from core.file_manager.model import FileManager
from core.file_manager.schema import FileManagerCreate, FileManagerUpdate
from core.file_manager.storage_backends import get_storage_backend


class FileManagerService(BaseService[FileManager, FileManagerCreate, FileManagerUpdate]):
    """文件管理服务"""
    
    model = FileManager

    @classmethod
    async def get_list(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        parent_id: Optional[str] = None,
        name: Optional[str] = None,
        type: Optional[str] = None,
        storage_type: Optional[str] = None,
        file_ext: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> Tuple[List[FileManager], int]:
        """获取文件列表"""
        # 构建查询条件
        conditions = [cls.model.is_deleted == False]  # noqa: E712
        
        # 父文件夹过滤
        if parent_id is None:
            conditions.append(cls.model.parent_id == None)  # noqa: E711
        else:
            conditions.append(cls.model.parent_id == parent_id)
        
        if name:
            conditions.append(cls.model.name.ilike(f"%{name}%"))
        if type:
            conditions.append(cls.model.type == type)
        if storage_type:
            conditions.append(cls.model.storage_type == storage_type)
        if file_ext:
            conditions.append(cls.model.file_ext == file_ext)
        if is_public is not None:
            conditions.append(cls.model.is_public == is_public)
        
        # 查询总数
        count_query = select(func.count(cls.model.id)).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 查询数据（文件夹排在前面）
        offset = (page - 1) * page_size
        query = (
            select(cls.model)
            .where(*conditions)
            .order_by(cls.model.type, cls.model.sys_create_datetime.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        items = result.scalars().all()
        
        return items, total

    @classmethod
    async def get_folder_tree(cls, db: AsyncSession) -> List[FileManager]:
        """获取文件夹树结构"""
        query = (
            select(cls.model)
            .where(
                cls.model.type == 'folder',
                cls.model.is_deleted == False  # noqa: E712
            )
            .order_by(cls.model.name)
        )
        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def create_folder(
        cls,
        db: AsyncSession,
        name: str,
        parent_id: Optional[str] = None,
        creator_id: Optional[str] = None,
    ) -> Optional[FileManager]:
        """创建文件夹"""
        # 获取父文件夹路径
        parent_path = ''
        if parent_id:
            parent = await cls.get_by_id(db, parent_id)
            if parent and parent.type == 'folder':
                parent_path = parent.path
        
        # 构建文件夹路径
        folder_path = os.path.join(parent_path, name).replace('\\', '/') if parent_path else name
        
        # 检查同名文件夹
        existing = await db.execute(
            select(cls.model).where(
                cls.model.parent_id == parent_id,
                cls.model.name == name,
                cls.model.type == 'folder',
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            return None  # 同名文件夹已存在
        
        # 创建文件夹
        folder = FileManager(
            name=name,
            type='folder',
            parent_id=parent_id,
            path=folder_path,
            storage_path='',
            sys_creator_id=creator_id,
        )
        db.add(folder)
        await db.commit()
        await db.refresh(folder)
        return folder

    @classmethod
    async def upload_file(
        cls,
        db: AsyncSession,
        file_content: bytes,
        filename: str,
        file_size: int,
        parent_id: Optional[str] = None,
        is_public: bool = False,
        creator_id: Optional[str] = None,
    ) -> FileManager:
        """上传文件"""
        # 获取父文件夹路径
        folder_path = ''
        if parent_id:
            parent = await cls.get_by_id(db, parent_id)
            if parent and parent.type == 'folder':
                folder_path = parent.path
        
        # 获取存储后端
        storage = get_storage_backend()
        
        # 计算文件信息
        file_ext = os.path.splitext(filename)[1].lower()
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        # 创建文件对象用于保存
        import io
        file_obj = io.BytesIO(file_content)
        
        # 计算MD5
        md5 = storage.calculate_md5(file_obj)
        file_obj.seek(0)
        
        # 保存文件
        storage_path, url = storage.save(file_obj, filename, folder_path)
        
        # 构建完整路径
        full_path = os.path.join(folder_path, filename).replace('\\', '/') if folder_path else filename
        
        # 创建数据库记录
        file_record = FileManager(
            name=filename,
            type='file',
            parent_id=parent_id,
            path=full_path,
            size=file_size,
            file_ext=file_ext,
            mime_type=mime_type,
            storage_type=storage.__class__.__name__.replace('StorageBackend', '').lower(),
            storage_path=storage_path,
            url=url,
            md5=md5,
            is_public=is_public,
            sys_creator_id=creator_id,
        )
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        return file_record

    @classmethod
    async def rename_item(
        cls,
        db: AsyncSession,
        item_id: str,
        new_name: str,
    ) -> Optional[FileManager]:
        """重命名文件/文件夹"""
        item = await cls.get_by_id(db, item_id)
        if not item:
            return None
        
        # 检查同级目录下是否有同名文件
        existing = await db.execute(
            select(cls.model).where(
                cls.model.parent_id == item.parent_id,
                cls.model.name == new_name,
                cls.model.type == item.type,
                cls.model.id != item_id,
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            return None  # 同名文件/文件夹已存在
        
        # 更新名称和路径
        old_path = item.path
        if item.parent_id:
            parent = await cls.get_by_id(db, item.parent_id)
            new_path = os.path.join(parent.path, new_name).replace('\\', '/') if parent else new_name
        else:
            new_path = new_name
        
        item.name = new_name
        item.path = new_path
        await db.commit()
        await db.refresh(item)
        
        # 如果是文件夹，递归更新子项路径
        if item.type == 'folder':
            await cls._update_children_paths(db, item.id, old_path, new_path)
        
        return item

    @classmethod
    async def move_items(
        cls,
        db: AsyncSession,
        item_ids: List[str],
        target_folder_id: Optional[str] = None,
    ) -> bool:
        """移动文件/文件夹"""
        # 获取目标文件夹
        target_path = ''
        if target_folder_id:
            target_folder = await cls.get_by_id(db, target_folder_id)
            if not target_folder or target_folder.type != 'folder':
                return False
            target_path = target_folder.path
        
        for item_id in item_ids:
            item = await cls.get_by_id(db, item_id)
            if not item:
                continue
            
            # 不能移动到自己或子文件夹
            if item.type == 'folder' and target_folder_id:
                if await cls._is_subfolder(db, target_folder_id, item.id):
                    continue
            
            # 检查目标文件夹是否有同名文件
            existing = await db.execute(
                select(cls.model).where(
                    cls.model.parent_id == target_folder_id,
                    cls.model.name == item.name,
                    cls.model.type == item.type,
                    cls.model.id != item_id,
                    cls.model.is_deleted == False  # noqa: E712
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            # 更新父文件夹和路径
            old_path = item.path
            item.parent_id = target_folder_id
            item.path = os.path.join(target_path, item.name).replace('\\', '/') if target_path else item.name
            
            # 如果是文件夹，递归更新子项路径
            if item.type == 'folder':
                await cls._update_children_paths(db, item.id, old_path, item.path)
        
        await db.commit()
        return True

    @classmethod
    async def delete_item(
        cls,
        db: AsyncSession,
        item_id: str,
        hard: bool = True,
    ) -> bool:
        """删除文件/文件夹"""
        item = await cls.get_by_id(db, item_id)
        if not item:
            return False
        
        # 如果是文件，删除实际文件
        if item.type == 'file':
            storage = get_storage_backend()
            storage.delete(item.storage_path)
        
        # 递归删除子项
        if item.type == 'folder':
            await cls._delete_children(db, item.id, hard)
        
        # 删除数据库记录
        if hard:
            await db.delete(item)
        else:
            item.is_deleted = True
        
        await db.commit()
        return True

    @classmethod
    async def batch_delete(
        cls,
        db: AsyncSession,
        item_ids: List[str],
        hard: bool = True,
    ) -> int:
        """批量删除文件/文件夹"""
        deleted_count = 0
        for item_id in item_ids:
            if await cls.delete_item(db, item_id, hard):
                deleted_count += 1
        return deleted_count

    @classmethod
    async def get_by_storage_path(
        cls,
        db: AsyncSession,
        storage_path: str,
    ) -> Optional[FileManager]:
        """通过存储路径获取文件"""
        result = await db.execute(
            select(cls.model).where(
                cls.model.storage_path == storage_path,
                cls.model.type == 'file',
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def increment_download_count(
        cls,
        db: AsyncSession,
        item_id: str,
    ) -> None:
        """增加下载次数"""
        item = await cls.get_by_id(db, item_id)
        if item:
            item.download_count += 1
            await db.commit()

    @classmethod
    async def get_by_md5(
        cls,
        db: AsyncSession,
        md5: str,
        size: int,
    ) -> Optional[FileManager]:
        """通过MD5和大小查找文件（用于秒传）"""
        result = await db.execute(
            select(cls.model).where(
                cls.model.md5 == md5,
                cls.model.size == size,
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def has_children(cls, db: AsyncSession, folder_id: str) -> bool:
        """检查文件夹是否有子项"""
        result = await db.execute(
            select(func.count(cls.model.id)).where(
                cls.model.parent_id == folder_id,
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        count = result.scalar() or 0
        return count > 0

    @classmethod
    async def get_parent(cls, db: AsyncSession, item_id: str) -> Optional[FileManager]:
        """获取父文件夹"""
        item = await cls.get_by_id(db, item_id)
        if item and item.parent_id:
            return await cls.get_by_id(db, item.parent_id)
        return None

    @classmethod
    async def _is_subfolder(cls, db: AsyncSession, folder_id: str, potential_parent_id: str) -> bool:
        """检查folder是否是potential_parent的子文件夹"""
        current_id = folder_id
        while current_id:
            current = await cls.get_by_id(db, current_id)
            if not current:
                break
            if current.parent_id == potential_parent_id:
                return True
            current_id = current.parent_id
        return False

    @classmethod
    async def _update_children_paths(cls, db: AsyncSession, folder_id: str, old_path: str, new_path: str) -> None:
        """递归更新子项路径"""
        result = await db.execute(
            select(cls.model).where(
                cls.model.parent_id == folder_id,
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        children = result.scalars().all()
        
        for child in children:
            child.path = child.path.replace(old_path, new_path, 1)
            if child.type == 'folder':
                await cls._update_children_paths(db, child.id, old_path, new_path)

    @classmethod
    async def _delete_children(cls, db: AsyncSession, folder_id: str, hard: bool = True) -> None:
        """递归删除子项"""
        result = await db.execute(
            select(cls.model).where(
                cls.model.parent_id == folder_id,
                cls.model.is_deleted == False  # noqa: E712
            )
        )
        children = result.scalars().all()
        
        storage = get_storage_backend()
        
        for child in children:
            # 如果是文件，删除实际文件
            if child.type == 'file':
                storage.delete(child.storage_path)
            
            # 递归删除子项
            if child.type == 'folder':
                await cls._delete_children(db, child.id, hard)
            
            # 删除数据库记录
            if hard:
                await db.delete(child)
            else:
                child.is_deleted = True
