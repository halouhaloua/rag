from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatConversationCreate(BaseModel):
    title: Optional[str] = "新对话"
    user_id: str
    model_name: Optional[str] = "qwen"


class ChatMessageCreate(BaseModel):
    conversation_id: str
    role: str
    content: str
    model_name: Optional[str] = None


class ChatRequest(BaseModel):
    user_id: str
    conversation_id: Optional[str] = None
    question: str
    model_name: Optional[str] = "qwen"
    dataset_name: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str | dict
    model_name: Optional[str]
    sys_create_datetime: datetime

    class Config:
        from_attributes = True


class ChatConversationResponse(BaseModel):
    id: str
    title: str
    user_id: str
    model_name: Optional[str]
    sys_create_datetime: datetime
    sys_update_datetime: datetime

    class Config:
        from_attributes = True
