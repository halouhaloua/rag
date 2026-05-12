from typing import List
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse

from graphrag.rag.schema import (
    FileUploadResponse,
    GraphConstructionRequest,
    GraphConstructionResponse,
    QuestionRequest,
)
from graphrag.rag.socket_manager import manager
from graphrag.rag.service import (
    process_upload_files,
    construct_graph_service,
    ask_question_service_stream,
    get_datasets_service,
    upload_schema_service,
    delete_dataset_service,
    reconstruct_dataset_service,
    get_graph_data_service,
    GRAPHRAG_AVAILABLE,
)

router = APIRouter(prefix="/api", tags=["rag"])


@router.get("/status")
async def get_status():
    return {
        "message": "Youtu-GraphRAG Unified Interface is running!",
        "status": "ok",
        "graphrag_available": GRAPHRAG_AVAILABLE,
    }


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_files(files: List[UploadFile] = File(...), client_id: str = "default"):
    try:
        dataset_name, files_count = await process_upload_files(files, client_id)
        return FileUploadResponse(
            success=True,
            message="Files uploaded successfully",
            dataset_name=dataset_name,
            files_count=files_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/construct-graph", response_model=GraphConstructionResponse)
async def construct_graph(
    request: GraphConstructionRequest, client_id: str = "default"
):
    try:
        if not GRAPHRAG_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="GraphRAG components not available."
            )
        graph_vis_data = await construct_graph_service(request.dataset_name, client_id)
        return GraphConstructionResponse(
            success=True,
            message="Knowledge graph constructed successfully",
            graph_data=graph_vis_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-question")
async def ask_question(request: QuestionRequest, client_id: str = "default"):
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="GraphRAG components not available."
        )
    return StreamingResponse(
        ask_question_service_stream(request.dataset_name, request.question, client_id),
        media_type="text/event-stream",
    )


@router.get("/datasets")
async def get_datasets():
    return await get_datasets_service()


@router.post("/datasets/{dataset_name}/schema")
async def upload_schema(dataset_name: str, schema_file: UploadFile = File(...)):
    try:
        result = await upload_schema_service(dataset_name, schema_file)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/datasets/{dataset_name}")
async def delete_dataset(dataset_name: str):
    try:
        result = await delete_dataset_service(dataset_name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/{dataset_name}/reconstruct")
async def reconstruct_dataset(dataset_name: str, client_id: str = "default"):
    try:
        if not GRAPHRAG_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="GraphRAG components not available."
            )
        result = await reconstruct_dataset_service(dataset_name, client_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/{dataset_name}")
async def get_graph_data(dataset_name: str):
    return await get_graph_data_service(dataset_name)
