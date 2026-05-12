from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.base_service import BaseService
from graphrag.retrieval.model import ChatConversation, ChatMessage
from graphrag.retrieval.schema import ChatConversationCreate, ChatMessageCreate


class ChatConversationService(
    BaseService[ChatConversation, ChatConversationCreate, BaseModel]
):
    model = ChatConversation
    excel_columns = {
        "id": "会话ID",
        "user_id": "用户ID",
        "title": "会话标题",
        "model_name": "使用模型",
        "sys_create_datetime": "创建时间",
        "sys_update_datetime": "更新时间",
    }
    excel_sheet_name = "对话会话列表"

    @classmethod
    async def get_user_conversations(
        cls, db: AsyncSession, user_id: str, page: int = 1, page_size: int = 20
    ) -> (List[ChatConversation], int):
        filters = [cls.model.user_id == user_id]
        return await cls.get_list(db, page=page, page_size=page_size, filters=filters)


class ChatMessageService(BaseService[ChatMessage, ChatMessageCreate, BaseModel]):
    model = ChatMessage
    excel_columns = {
        "id": "消息ID",
        "conversation_id": "会话ID",
        "role": "角色",
        "content": "内容",
        "model_name": "模型",
        "prompt_tokens": "输入Token",
        "completion_tokens": "输出Token",
        "total_tokens": "总Token",
        "sys_create_datetime": "发送时间",
    }
    excel_sheet_name = "对话消息记录"

    @classmethod
    async def get_messages_by_conversation(
        cls, db: AsyncSession, conversation_id: str
    ) -> List[ChatMessage]:
        query = (
            select(cls.model)
            .where(
                cls.model.conversation_id == conversation_id,
                cls.model.is_deleted == False,  # noqa: E712
            )
            .order_by(cls.model.sys_create_datetime.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())
