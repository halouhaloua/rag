from typing import List, Optional
import json
import mimetypes
import pathlib
from urllib.parse import parse_qs, quote

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

from graphrag.rag.schema import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseFileResponse,
    KnowledgeBaseFileListResponse,
    FileSchemaUpdate,
    FileUploadResponseWrapper,
    ConstructGraphResponse,
    QuestionRequest,
    DeleteResponse,
    GraphCategoryUpdate,
    GraphNodesCreate,
    GraphEdgesCreate,
    GraphEdgeDeleteRequest,
    GraphEdgeUpdateRequest,
)
from graphrag.rag.service import (
    GRAPHRAG_AVAILABLE,
    DATA_UPLOAD_DIR,
    upload_files_to_kb,
    construct_file_graph_service,
    ask_file_question_stream,
    get_file_graph_service,
    update_node_category_service,
    add_graph_edges_service,
    add_graph_nodes_service,
    delete_graph_node_service,
    delete_graph_edge_service,
    update_graph_edge_service,
    get_file_graph_nodes_service,
    get_file_graph_edges_service,
)
from graphrag.rag.db_service import (
    KnowledgeBaseService,
    KnowledgeBaseFileService,
    KnowledgeGraphService,
)
from graphrag.rag.socket_manager import manager
from utils.security import verify_access_token, get_current_user
from core.user.model import User
from graphrag.kb_manager.service import KnowledgeBasePermissionService

router = APIRouter(prefix="/api", tags=["知识库管理"])
ws_router = APIRouter(prefix="/api", tags=["知识图谱WebSocket"])


# ──────────────────────────────────────────────
# WebSocket (token auth from query string)
# ──────────────────────────────────────────────
@ws_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    query_string = websocket.scope.get('query_string', b'').decode('utf-8')
    token = None
    if query_string:
        query_params = parse_qs(query_string)
        token_list = query_params.get('token', [])
        if token_list:
            token = token_list[0]

    if not token or not verify_access_token(token):
        await websocket.accept()
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)


@router.get("/status")
async def get_status():
    return {
        "message": "Youtu-GraphRAG Unified Interface is running!",
        "status": "ok",
        "graphrag_available": GRAPHRAG_AVAILABLE,
    }


# ──────────────────────────────────────────────
# Knowledge Base CRUD
# ──────────────────────────────────────────────
@router.post("/knowledge-base", response_model=KnowledgeBaseResponse, summary="创建知识库")
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await KnowledgeBaseService.get_by_field(db, field="name", value=data.name)
    if existing:
        raise HTTPException(status_code=400, detail="知识库名称已存在")
    return await KnowledgeBaseService.create(db, data)


@router.get("/knowledge-bases", response_model=KnowledgeBaseListResponse, summary="知识库列表")
async def list_knowledge_bases(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=200, ge=1, le=500, alias="pageSize"),
    name: str = Query(default=None, description="知识库名称搜索"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import select as sa_select, func as sa_func
    from graphrag.rag.model import KnowledgeBaseFile

    kb_ids = await KnowledgeBasePermissionService.get_user_visible_kb_ids(db, user)
    if kb_ids is not None:
        base_query = (
            sa_select(KnowledgeBaseService.model)
            .where(
                KnowledgeBaseService.model.id.in_(kb_ids),
                KnowledgeBaseService.model.is_deleted == False,
            )
        )
        if name:
            base_query = base_query.where(KnowledgeBaseService.model.name.ilike(f"%{name}%"))
        count_result = await db.execute(sa_select(sa_func.count()).select_from(base_query.subquery()))
        total = count_result.scalar() or 0
        offset = (page - 1) * page_size
        result = await db.execute(
            base_query.order_by(
                KnowledgeBaseService.model.sort.desc(),
                KnowledgeBaseService.model.sys_create_datetime.desc(),
            ).offset(offset).limit(page_size)
        )
        items = list(result.scalars().all())
    else:
        items, total = await KnowledgeBaseService.get_list_with_file_count(
            db, page=page, page_size=page_size, name=name
        )

    for item in items:
        count_query = (
            sa_select(sa_func.count(KnowledgeBaseFile.id))
            .where(
                KnowledgeBaseFile.kb_id == item.id,
                KnowledgeBaseFile.is_deleted == False,
            )
        )
        cnt = await db.execute(count_query)
        item.file_count = cnt.scalar() or 0

    return KnowledgeBaseListResponse(items=items, total=total)


@router.get("/knowledge-base/{kb_id}", response_model=KnowledgeBaseResponse, summary="知识库详情")
async def get_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kb = await KnowledgeBaseService.get_by_id(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    kb.file_count = await KnowledgeBaseFileService.count_by_kb(db, kb_id)
    return kb


@router.put("/knowledge-base/{kb_id}", response_model=KnowledgeBaseResponse, summary="更新知识库")
async def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    if data.name:
        existing = await KnowledgeBaseService.get_by_field(db, field="name", value=data.name)
        if existing and existing.id != kb_id:
            raise HTTPException(status_code=400, detail="知识库名称已存在")
    result = await KnowledgeBaseService.update(db, record_id=kb_id, data=data)
    if not result:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return result


@router.delete("/knowledge-base/{kb_id}", summary="删除知识库")
async def delete_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    kb = await KnowledgeBaseService.get_by_id(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    from graphrag.rag.service import clear_cache_files
    files = await KnowledgeBaseFileService.get_files_by_kb(db, kb_id)
    for f in files:
        await clear_cache_files(kb_id, f.id)
        await KnowledgeGraphService.delete_by_file(db, f.id)
        await KnowledgeBaseFileService.delete(db, f.id)
    success = await KnowledgeBaseService.delete(db, kb_id)
    if not success:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return DeleteResponse(msg="知识库删除成功")


# ──────────────────────────────────────────────
# File Management
# ──────────────────────────────────────────────
@router.post(
    "/knowledge-base/{kb_id}/files/upload",
    summary="上传文件到知识库",
)
async def upload_kb_files(
    kb_id: str,
    files: List[UploadFile] = File(...),
    schema_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kb = await KnowledgeBaseService.get_by_id(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")

    schema_json = None
    if schema_file:
        try:
            schema_content = await schema_file.read()
            schema_json = json.loads(schema_content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Schema文件格式错误，需要JSON格式")

    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")

    try:
        results = await upload_files_to_kb(kb_id, files, schema_json, db)
        return FileUploadResponseWrapper(items=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/knowledge-base/{kb_id}/files",
    response_model=KnowledgeBaseFileListResponse,
    summary="文件列表",
)
async def list_kb_files(kb_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    kb = await KnowledgeBaseService.get_by_id(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    files = await KnowledgeBaseFileService.get_files_by_kb(db, kb_id)
    return KnowledgeBaseFileListResponse(items=files, total=len(files))


@router.get(
    "/knowledge-base/{kb_id}/files/{file_id}",
    response_model=KnowledgeBaseFileResponse,
    summary="文件详情",
)
async def get_kb_file(kb_id: str, file_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    return f


@router.get(
    "/knowledge-base/{kb_id}/files/{file_id}/preview",
    summary="文件预览（PDF/Word/文本）",
)
async def preview_kb_file(
    kb_id: str, file_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    ext = f.file_type or ".bin"
    file_path = DATA_UPLOAD_DIR / kb_id / f"{file_id}{ext}"
    if file_path.exists():
        media_type, _ = mimetypes.guess_type(str(file_path))
        disposition = f"inline; filename*=UTF-8''{quote(f.filename)}"
        return FileResponse(
            str(file_path),
            media_type=media_type or "application/octet-stream",
            headers={"Content-Disposition": disposition},
        )
    content = f.content or "(无内容)"
    media_type = "text/plain; charset=utf-8"
    return Response(content=content, media_type=media_type)


@router.get(
    "/knowledge-base/{kb_id}/files/{file_id}/content",
    summary="文件提取文本内容",
)
async def get_kb_file_content(
    kb_id: str, file_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"content": f.content or "", "filename": f.filename}


@router.put(
    "/knowledge-base/{kb_id}/files/{file_id}/schema",
    summary="更新文件Schema",
)
async def update_file_schema(
    kb_id: str, file_id: str, data: FileSchemaUpdate, db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    f.schema_json = data.schema_definition
    await db.flush()
    await db.commit()
    return {"msg": "Schema更新成功"}


@router.delete(
    "/knowledge-base/{kb_id}/files/{file_id}",
    summary="删除文件",
)
async def delete_kb_file(kb_id: str, file_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    from graphrag.rag.service import clear_cache_files
    await clear_cache_files(kb_id, file_id)
    await KnowledgeGraphService.delete_by_file(db, file_id)
    success = await KnowledgeBaseFileService.delete(db, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    return DeleteResponse(msg="文件删除成功")


@router.put(
    "/knowledge-base/{kb_id}/files/{file_id}/graph/edge",
    summary="编辑单条边",
)
async def update_graph_edge(
    kb_id: str,
    file_id: str,
    data: GraphEdgeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    try:
        return await update_graph_edge_service(
            file_id,
            data.source, data.relation, data.target,
            new_source=data.new_source,
            new_relation=data.new_relation,
            new_target=data.new_target,
            new_source_category=data.new_source_category,
            new_target_category=data.new_target_category,
            db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/knowledge-base/{kb_id}/files/{file_id}/construct-graph",
    summary="构建文件图谱",
)
async def construct_file_graph(
    kb_id: str,
    file_id: str,
    client_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="GraphRAG components not available.")

    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        graph_vis_data = await construct_file_graph_service(file_id, client_id, db)
        return ConstructGraphResponse(
            success=True, message="图谱构建成功", graph_data=graph_vis_data
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/knowledge-base/{kb_id}/files/{file_id}/graph",
    summary="获取图谱可视化数据",
)
async def get_file_graph(kb_id: str, file_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    return await get_file_graph_service(file_id, db)


@router.get(
    "/knowledge-base/{kb_id}/files/{file_id}/graph/nodes",
    summary="分页获取节点列表",
)
async def get_file_graph_nodes(
    kb_id: str,
    file_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    return await get_file_graph_nodes_service(file_id, page, page_size, db)


@router.get(
    "/knowledge-base/{kb_id}/files/{file_id}/graph/edges",
    summary="分页获取边列表",
)
async def get_file_graph_edges(
    kb_id: str,
    file_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    return await get_file_graph_edges_service(file_id, page, page_size, db)


# ──────────────────────────────────────────────
# Triple Management
# ──────────────────────────────────────────────
@router.put(
    "/knowledge-base/{kb_id}/files/{file_id}/graph/node/category",
    summary="修改节点类别",
)
async def update_graph_node_category(
    kb_id: str,
    file_id: str,
    data: GraphCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    try:
        return await update_node_category_service(file_id, data.node_name, data.new_category, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/knowledge-base/{kb_id}/files/{file_id}/graph/edges",
    summary="批量添加边",
)
async def add_graph_edges(
    kb_id: str,
    file_id: str,
    data: GraphEdgesCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    try:
        return await add_graph_edges_service(file_id, [e.model_dump() for e in data.edges], db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/knowledge-base/{kb_id}/files/{file_id}/graph/nodes",
    summary="批量添加节点",
)
async def add_graph_nodes(
    kb_id: str,
    file_id: str,
    data: GraphNodesCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    try:
        return await add_graph_nodes_service(file_id, [n.model_dump() for n in data.nodes], db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/knowledge-base/{kb_id}/files/{file_id}/graph/nodes/{node_name}",
    summary="删除节点（连带所有关联边）",
)
async def delete_graph_node(
    kb_id: str,
    file_id: str,
    node_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    try:
        return await delete_graph_node_service(file_id, node_name, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/knowledge-base/{kb_id}/files/{file_id}/graph/edge",
    summary="删除单条边",
)
async def delete_graph_edge(
    kb_id: str,
    file_id: str,
    data: GraphEdgeDeleteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    try:
        return await delete_graph_edge_service(file_id, data.source, data.relation, data.target, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/knowledge-base/{kb_id}/files/{file_id}/reconstruct",
    summary="重建文件图谱",
)
async def reconstruct_file_graph(
    kb_id: str,
    file_id: str,
    client_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="GraphRAG components not available.")

    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")

    await KnowledgeGraphService.delete_by_file(db, file_id)
    await KnowledgeBaseFileService.update_file_graph_status(db, file_id, False)

    try:
        graph_vis_data = await construct_file_graph_service(file_id, client_id, db)
        return ConstructGraphResponse(
            success=True, message="图谱重建成功", graph_data=graph_vis_data
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# Question Answering
# ──────────────────────────────────────────────
@router.post(
    "/knowledge-base/{kb_id}/files/{file_id}/ask-question",
    summary="针对文件提问（SSE流式）",
)
async def ask_file_question(
    kb_id: str,
    file_id: str,
    request: QuestionRequest,
    client_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="GraphRAG components not available.")

    if not await KnowledgeBasePermissionService.check_kb_access(db, kb_id, user):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱，请先构建")

    return StreamingResponse(
        ask_file_question_stream(file_id, request.question, client_id, db),
        media_type="text/event-stream",
    )
