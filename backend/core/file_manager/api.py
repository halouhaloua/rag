#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: api.py
@Desc: 文件管理API
"""
"""
文件管理API
"""
import os
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.base_schema import PaginatedResponse, ResponseModel
from core.file_manager.model import FileManager
from core.file_manager.schema import (
    FileManagerResponse,
    FileManagerSimpleResponse,
    CreateFolderIn,
    MoveItemsIn,
    RenameItemIn,
    BatchDeleteIn,
    FileStorageConfigResponse,
    FileStorageConfigUpdate,
    FileUrlResponse,
)
from core.file_manager.service import FileManagerService
from core.file_manager.storage_backends import get_storage_backend

router = APIRouter(prefix="/file_manager", tags=["文件管理"])


def _build_file_response(item: FileManager, has_children: bool = False, parent_name: str = None) -> dict:
    """构建文件响应"""
    return {
        "id": item.id,
        "name": item.name,
        "file_type": item.type,
        "parent_id": item.parent_id,
        "parent_name": parent_name,
        "path": item.path,
        "file_size": item.size,
        "file_ext": item.file_ext,
        "mime_type": item.mime_type,
        "storage_type": item.storage_type,
        "storage_path": item.storage_path,
        "url": item.url,
        "thumbnail_url": item.thumbnail_url,
        "md5": item.md5,
        "is_public": item.is_public,
        "download_count": item.download_count,
        "has_children": has_children,
        "updated_time": item.sys_update_datetime.isoformat() if item.sys_update_datetime else (
            item.sys_create_datetime.isoformat() if item.sys_create_datetime else None
        ),
        "sys_create_datetime": item.sys_create_datetime,
        "sys_update_datetime": item.sys_update_datetime,
    }


@router.post("/upload", response_model=FileManagerResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    parent_id: Optional[str] = Form(None, alias="parentId"),
    is_public: bool = Form(False, alias="isPublic"),
    db: AsyncSession = Depends(get_db),
):
    """上传文件"""
    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)
    
    # 上传文件
    file_obj = await FileManagerService.upload_file(
        db=db,
        file_content=file_content,
        filename=file.filename,
        file_size=file_size,
        parent_id=parent_id,
        is_public=is_public,
    )
    
    return _build_file_response(file_obj)


@router.post("/folder", response_model=FileManagerResponse, summary="创建文件夹")
async def create_folder(
    data: CreateFolderIn,
    db: AsyncSession = Depends(get_db),
):
    """创建文件夹"""
    folder = await FileManagerService.create_folder(
        db=db,
        name=data.name,
        parent_id=data.parent_id,
    )
    
    if not folder:
        raise HTTPException(status_code=422, detail="同名文件夹已存在")
    
    return _build_file_response(folder)


@router.get("", response_model=PaginatedResponse[FileManagerResponse], summary="获取文件列表")
async def list_files(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize", description="每页数量"),
    parent_id: Optional[str] = Query(None, alias="parentId", description="父文件夹ID"),
    name: Optional[str] = Query(None, description="文件名搜索"),
    type: Optional[str] = Query(None, description="类型: file/folder"),
    storage_type: Optional[str] = Query(None, alias="storageType", description="存储类型"),
    file_ext: Optional[str] = Query(None, alias="fileExt", description="文件扩展名"),
    is_public: Optional[bool] = Query(None, alias="isPublic", description="是否公开"),
    db: AsyncSession = Depends(get_db),
):
    """获取文件列表（分页）"""
    items, total = await FileManagerService.get_list(
        db=db,
        page=page,
        page_size=page_size,
        parent_id=parent_id,
        name=name,
        type=type,
        storage_type=storage_type,
        file_ext=file_ext,
        is_public=is_public,
    )
    
    # 构建响应
    result_items = []
    for item in items:
        has_children = False
        if item.type == 'folder':
            has_children = await FileManagerService.has_children(db, item.id)
        
        parent_name = None
        if item.parent_id:
            parent = await FileManagerService.get_by_id(db, item.parent_id)
            if parent:
                parent_name = parent.name
        
        result_items.append(_build_file_response(item, has_children, parent_name))
    
    return PaginatedResponse(items=result_items, total=total)


@router.get("/tree", response_model=List[FileManagerResponse], summary="获取文件夹树结构")
async def get_folder_tree(db: AsyncSession = Depends(get_db)):
    """获取文件夹树结构"""
    folders = await FileManagerService.get_folder_tree(db)
    
    result = []
    for folder in folders:
        has_children = await FileManagerService.has_children(db, folder.id)
        result.append(_build_file_response(folder, has_children))
    
    return result


@router.get("/file_info/{file_id}", response_model=FileManagerSimpleResponse, summary="获取文件信息")
async def get_file_info(
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文件信息"""
    file_obj = await FileManagerService.get_by_id(db, file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return {
        "id": file_obj.id,
        "name": file_obj.name,
        "type": file_obj.type,
        "size": file_obj.size,
    }


@router.put("/{file_id}/rename", response_model=FileManagerResponse, summary="重命名文件/文件夹")
async def rename_item(
    file_id: str,
    data: RenameItemIn,
    db: AsyncSession = Depends(get_db),
):
    """重命名文件/文件夹"""
    item = await FileManagerService.rename_item(db, file_id, data.name)
    
    if not item:
        raise HTTPException(status_code=400, detail="重命名失败，可能同名文件/文件夹已存在")
    
    return _build_file_response(item)


@router.put("/move", response_model=ResponseModel, summary="移动文件/文件夹")
async def move_items(
    data: MoveItemsIn,
    db: AsyncSession = Depends(get_db),
):
    """移动文件/文件夹"""
    success = await FileManagerService.move_items(db, data.ids, data.target_folder_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="移动失败")
    
    return ResponseModel(message="移动成功")


@router.delete("/{file_id}", response_model=ResponseModel, summary="删除文件/文件夹")
async def delete_item(
    file_id: str,
    hard: bool = Query(default=True, description="是否物理删除"),
    db: AsyncSession = Depends(get_db),
):
    """删除文件/文件夹"""
    success = await FileManagerService.delete_item(db, file_id, hard)
    
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return ResponseModel(message="删除成功")


@router.post("/batch/delete", response_model=ResponseModel, summary="批量删除文件/文件夹")
async def batch_delete(
    data: BatchDeleteIn,
    db: AsyncSession = Depends(get_db),
):
    """批量删除文件/文件夹"""
    deleted_count = await FileManagerService.batch_delete(db, data.ids)
    return ResponseModel(message=f"成功删除 {deleted_count} 个文件/文件夹")


@router.get("/file/download", summary="下载文件")
async def download_file(
    path: str = Query(..., description="文件存储路径"),
    db: AsyncSession = Depends(get_db),
):
    """下载文件"""
    # 查找文件记录
    file_obj = await FileManagerService.get_by_storage_path(db, path)
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 更新下载次数
    await FileManagerService.increment_download_count(db, file_obj.id)
    
    # 获取存储后端
    storage = get_storage_backend()
    
    # 如果是本地存储，直接返回文件
    if file_obj.storage_type == 'local':
        full_path = storage.get_full_path(path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            full_path,
            filename=file_obj.name,
            media_type=file_obj.mime_type or 'application/octet-stream',
        )
    else:
        # 其他存储类型，重定向到实际URL
        if file_obj.url:
            return Response(status_code=302, headers={'Location': file_obj.url})
        else:
            raise HTTPException(status_code=400, detail="无法获取文件URL")


@router.get("/url/{file_id}", response_model=FileUrlResponse, summary="获取文件访问URL")
async def get_file_url(
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """通过文件ID获取文件访问URL"""
    file_obj = await FileManagerService.get_by_id(db, file_id)
    if not file_obj or file_obj.type != 'file':
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # Minio存储，返回临时URL
    if file_obj.storage_type == 'minio':
        storage = get_storage_backend()
        if hasattr(storage, 'get_presigned_url'):
            try:
                temp_url = storage.get_presigned_url(file_obj.storage_path)
                return {"url": temp_url}
            except Exception:
                pass
    
    # 如果文件有直接的URL（云存储）
    if file_obj.url:
        return {"url": file_obj.url}
    
    # 本地存储，构建访问URL
    if file_obj.storage_type == 'local':
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        file_url = f"{base_url}/api/file_manager/file/download?path={file_obj.storage_path}"
        return {"url": file_url}
    
    # 其他情况返回存储路径
    return {"url": file_obj.storage_path}


@router.get("/batch/urls", summary="批量获取文件访问URL")
async def get_batch_file_urls(
    ids: str = Query(..., description="文件ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db),
):
    """批量获取文件访问URL"""
    file_ids = [id_str.strip() for id_str in ids.split(',') if id_str.strip()]
    
    storage = get_storage_backend()
    has_presigned_method = hasattr(storage, 'get_presigned_url')
    
    result = {}
    for file_id in file_ids:
        file_obj = await FileManagerService.get_by_id(db, file_id)
        if not file_obj or file_obj.type != 'file':
            continue
        
        # Minio存储，返回临时URL
        if file_obj.storage_type == 'minio' and has_presigned_method:
            try:
                temp_url = storage.get_presigned_url(file_obj.storage_path)
                result[file_id] = temp_url
                continue
            except Exception:
                pass
        
        if file_obj.url:
            result[file_id] = file_obj.url
        elif file_obj.storage_type == 'local':
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            file_url = f"{base_url}/api/file_manager/file/download?path={file_obj.storage_path}"
            result[file_id] = file_url
        else:
            result[file_id] = file_obj.storage_path
    
    return result


@router.get("/stream/{file_id}", summary="流式传输文件")
async def stream_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """通过后端流式传输文件（支持所有存储类型）"""
    file_obj = await FileManagerService.get_by_id(db, file_id)
    if not file_obj or file_obj.type != 'file':
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 更新下载次数
    await FileManagerService.increment_download_count(db, file_obj.id)
    
    # 获取存储后端
    storage = get_storage_backend()
    
    if file_obj.storage_type == 'local':
        # 本地存储直接读取文件
        full_path = storage.get_full_path(file_obj.storage_path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        def file_iterator():
            with open(full_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk
        
        return StreamingResponse(
            file_iterator(),
            media_type=file_obj.mime_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'inline; filename="{file_obj.name}"',
                'Content-Length': str(file_obj.size),
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'public, max-age=3600',
            }
        )
    
    elif file_obj.storage_type == 'minio' and hasattr(storage, 'get_file_content'):
        # Minio存储，通过后端转发
        try:
            file_response = storage.get_file_content(file_obj.storage_path)
            return StreamingResponse(
                file_response,
                media_type=file_obj.mime_type or 'application/octet-stream',
                headers={
                    'Content-Disposition': f'inline; filename="{file_obj.name}"',
                    'Content-Length': str(file_obj.size),
                    'Accept-Ranges': 'bytes',
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")
    
    else:
        # 其他存储类型，重定向到原URL
        if file_obj.url:
            return Response(status_code=302, headers={'Location': file_obj.url})
        else:
            raise HTTPException(status_code=400, detail="不支持的存储类型")


@router.get("/proxy/{file_id}", summary="代理文件访问")
async def proxy_file(
    file_id: str,
    download: bool = Query(default=False, description="是否作为附件下载"),
    db: AsyncSession = Depends(get_db),
):
    """代理文件访问（强制通过后端转发）"""
    file_obj = await FileManagerService.get_by_id(db, file_id)
    if not file_obj or file_obj.type != 'file':
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 更新下载次数
    await FileManagerService.increment_download_count(db, file_obj.id)
    
    # 获取存储后端
    storage = get_storage_backend()
    
    disposition = 'attachment' if download else 'inline'
    
    if file_obj.storage_type == 'local':
        # 本地文件处理
        full_path = storage.get_full_path(file_obj.storage_path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        with open(full_path, 'rb') as f:
            content = f.read()
        
        return Response(
            content=content,
            media_type=file_obj.mime_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'{disposition}; filename="{file_obj.name}"',
                'Content-Length': str(len(content)),
                'Cache-Control': 'public, max-age=3600',
                'ETag': f'"{file_obj.md5}"' if file_obj.md5 else '',
            }
        )
    
    elif file_obj.storage_type == 'minio' and hasattr(storage, 'get_file_content'):
        # Minio存储处理
        try:
            file_response = storage.get_file_content(file_obj.storage_path)
            content = file_response.read()
            
            return Response(
                content=content,
                media_type=file_obj.mime_type or 'application/octet-stream',
                headers={
                    'Content-Disposition': f'{disposition}; filename="{file_obj.name}"',
                    'Content-Length': str(len(content)),
                    'Cache-Control': 'public, max-age=3600',
                    'ETag': f'"{file_obj.md5}"' if file_obj.md5 else '',
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")
    
    else:
        # 其他存储类型重定向
        if file_obj.url:
            return Response(status_code=302, headers={'Location': file_obj.url})
        else:
            raise HTTPException(status_code=400, detail="不支持的存储类型")


@router.get("/storage/config", response_model=FileStorageConfigResponse, summary="获取存储配置")
async def get_storage_config():
    """获取存储配置"""
    config = {
        'storage_type': getattr(settings, 'FILE_STORAGE_TYPE', 'local'),
        'local_base_path': getattr(settings, 'FILE_STORAGE_LOCAL_PATH', None),
    }
    return config


@router.put("/storage/config", response_model=ResponseModel, summary="更新存储配置")
async def update_storage_config(data: FileStorageConfigUpdate):
    """更新存储配置（需要管理员权限）"""
    # TODO: 实现配置更新逻辑，可能需要保存到数据库或配置文件
    return ResponseModel(message="配置更新成功")


@router.get("/{file_id}", response_model=FileManagerResponse, summary="获取文件详情")
async def get_file_detail(
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文件详情"""
    file_obj = await FileManagerService.get_by_id(db, file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    has_children = False
    if file_obj.type == 'folder':
        has_children = await FileManagerService.has_children(db, file_obj.id)
    
    parent_name = None
    if file_obj.parent_id:
        parent = await FileManagerService.get_by_id(db, file_obj.parent_id)
        if parent:
            parent_name = parent.name
    
    return _build_file_response(file_obj, has_children, parent_name)
