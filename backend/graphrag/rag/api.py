from typing import List, Optional
import json

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
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.base_schema import ResponseModel

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
)
from graphrag.rag.service import (
    GRAPHRAG_AVAILABLE,
    upload_files_to_kb,
    construct_file_graph_service,
    ask_file_question_stream,
    get_file_graph_service,
)
from graphrag.rag.db_service import (
    KnowledgeBaseService,
    KnowledgeBaseFileService,
    KnowledgeGraphService,
)
from graphrag.rag.socket_manager import manager

router = APIRouter(prefix="/api", tags=["知识库管理"])


# ──────────────────────────────────────────────
# WebSocket (unchanged)
# ──────────────────────────────────────────────
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
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
    data: KnowledgeBaseCreate, db: AsyncSession = Depends(get_db)
):
    existing = await KnowledgeBaseService.get_by_field(db, field="name", value=data.name)
    if existing:
        raise HTTPException(status_code=400, detail="知识库名称已存在")
    return await KnowledgeBaseService.create(db, data)


@router.get("/knowledge-bases", response_model=KnowledgeBaseListResponse, summary="知识库列表")
async def list_knowledge_bases(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=200, ge=1, le=500, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await KnowledgeBaseService.get_list_with_file_count(
        db, page=page, page_size=page_size
    )
    return KnowledgeBaseListResponse(items=items, total=total)


@router.get("/knowledge-base/{kb_id}", response_model=KnowledgeBaseResponse, summary="知识库详情")
async def get_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    kb = await KnowledgeBaseService.get_by_id(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    kb.file_count = await KnowledgeBaseFileService.count_by_kb(db, kb_id)
    return kb


@router.put("/knowledge-base/{kb_id}", response_model=KnowledgeBaseResponse, summary="更新知识库")
async def update_knowledge_base(
    kb_id: str, data: KnowledgeBaseUpdate, db: AsyncSession = Depends(get_db)
):
    if data.name:
        existing = await KnowledgeBaseService.get_by_field(db, field="name", value=data.name)
        if existing and existing.id != kb_id:
            raise HTTPException(status_code=400, detail="知识库名称已存在")
    result = await KnowledgeBaseService.update(db, record_id=kb_id, data=data)
    if not result:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return result


@router.delete("/knowledge-base/{kb_id}", summary="删除知识库")
async def delete_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    kb = await KnowledgeBaseService.get_by_id(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    from graphrag.rag.service import clear_kb_cache
    await clear_kb_cache(kb_id)
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
):
    kb = await KnowledgeBaseService.get_by_id(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

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
async def list_kb_files(kb_id: str, db: AsyncSession = Depends(get_db)):
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
async def get_kb_file(kb_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    return f


@router.put(
    "/knowledge-base/{kb_id}/files/{file_id}/schema",
    summary="更新文件Schema",
)
async def update_file_schema(
    kb_id: str, file_id: str, data: FileSchemaUpdate, db: AsyncSession = Depends(get_db)
):
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    f.schema_json = data.schema_definition
    await db.flush()
    return {"msg": "Schema更新成功"}


@router.delete(
    "/knowledge-base/{kb_id}/files/{file_id}",
    summary="删除文件",
)
async def delete_kb_file(kb_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    from graphrag.rag.service import clear_cache_files
    await clear_cache_files(kb_id, file_id)
    success = await KnowledgeBaseFileService.delete(db, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    return DeleteResponse(msg="文件删除成功")


# ──────────────────────────────────────────────
# Graph Construction
# ──────────────────────────────────────────────
@router.post(
    "/knowledge-base/{kb_id}/files/{file_id}/construct-graph",
    summary="构建文件图谱",
)
async def construct_file_graph(
    kb_id: str,
    file_id: str,
    client_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
):
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="GraphRAG components not available.")

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
async def get_file_graph(kb_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱")
    return await get_file_graph_service(file_id, db)


@router.post(
    "/knowledge-base/{kb_id}/files/{file_id}/reconstruct",
    summary="重建文件图谱",
)
async def reconstruct_file_graph(
    kb_id: str,
    file_id: str,
    client_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
):
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="GraphRAG components not available.")

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
):
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="GraphRAG components not available.")

    f = await KnowledgeBaseFileService.get_by_id(db, file_id)
    if not f or f.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not f.has_graph:
        raise HTTPException(status_code=400, detail="该文件尚未构建图谱，请先构建")

    return StreamingResponse(
        ask_file_question_stream(file_id, request.question, client_id, db),
        media_type="text/event-stream",
    )
