import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from graphrag.app.database import get_db, AsyncSessionLocal
from graphrag.retrieval.schema import (
    ChatConversationCreate,
    ChatMessageCreate,
    ChatConversationResponse,
    ChatMessageResponse,
    ChatRequest,
)
from graphrag.retrieval.service import (
    ChatConversationService,
    ChatMessageService,
    ChatConversation,
)
from graphrag.rag.service import ask_question_service_stream

router = APIRouter(prefix="/chat", tags=["聊天记录增删改查"])


@router.post("/conversation/create", response_model=ChatConversationResponse)
async def create_conversation(
    data: ChatConversationCreate, db: AsyncSession = Depends(get_db)
):
    return await ChatConversationService.create(db, data)


@router.get("/conversations/{user_id}", response_model=List[ChatConversationResponse])
async def get_user_conversations(
    user_id: str, page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)
):
    items, total = await ChatConversationService.get_user_conversations(
        db, user_id, page, page_size
    )
    return items


@router.get("/history/{conversation_id}", response_model=List[ChatMessageResponse])
async def get_chat_history(conversation_id: str, db: AsyncSession = Depends(get_db)):
    return await ChatMessageService.get_messages_by_conversation(db, conversation_id)


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    success = await ChatConversationService.delete(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"msg": "删除成功"}


async def _sse_stream_with_persistence(req: ChatRequest, conversation_id: str):
    answer_parts: List[str] = []
    sub_questions = []
    retrieved_triples = []
    retrieved_chunks = []
    reasoning_steps = []
    visualization_data = {}

    async for raw_event in ask_question_service_stream(
        req.dataset_name or "demo", req.question, req.user_id
    ):
        if raw_event.startswith("data: "):
            try:
                data = json.loads(raw_event[6:])
                if data["type"] == "token":
                    if data.get("phase") != "reasoning":
                        answer_parts.append(data["text"])
                elif data["type"] == "metadata":
                    sub_questions = data.get("sub_questions", [])
                    retrieved_triples = data.get("triples", [])
                    retrieved_chunks = data.get("chunks", [])
                elif data["type"] == "reasoning_steps":
                    reasoning_steps = data.get("data", {}).get("reasoning_steps", [])
                elif data["type"] == "visualization":
                    visualization_data = data.get("data", {})
                elif data["type"] == "done":
                    full_answer = data.get("answer", "".join(answer_parts))
                    ai_content = {
                        "answer": full_answer,
                        "sub_questions": sub_questions,
                        "retrieved_triples": retrieved_triples,
                        "retrieved_chunks": retrieved_chunks,
                        "reasoning_steps": reasoning_steps,
                        "visualization_data": visualization_data,
                    }
                    ai_msg = ChatMessageCreate(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=json.dumps(ai_content, ensure_ascii=False),
                        model_name=req.model_name,
                    )
                    async with AsyncSessionLocal() as sess:
                        await ChatMessageService.create(sess, ai_msg)
                    data["conversation_id"] = conversation_id
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    continue
            except json.JSONDecodeError:
                pass
        yield raw_event


@router.post("/message/chat")
async def chat_completion(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not req.conversation_id:
        conv_data = ChatConversationCreate(
            user_id=req.user_id,
            title=req.question[:20] + "...",
            model_name=req.model_name,
        )
        conv: ChatConversation = await ChatConversationService.create(db, conv_data)
        conversation_id = conv.id
    else:
        conversation_id = req.conversation_id

    user_msg = ChatMessageCreate(
        conversation_id=conversation_id,
        role="user",
        content=req.question,
        model_name=req.model_name,
    )
    await ChatMessageService.create(db, user_msg)

    return StreamingResponse(
        _sse_stream_with_persistence(req, conversation_id),
        media_type="text/event-stream",
    )
