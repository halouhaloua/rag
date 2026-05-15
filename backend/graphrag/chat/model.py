from sqlalchemy import Column, String, Text, Boolean, Integer
from app.base_model import BaseModel as AppBaseModel
from app.database import Base
from app.database import engine
import asyncio


class ChatConversation(AppBaseModel):
    __tablename__ = "chat_conversations"
    title = Column(String(200), nullable=False, default="新对话", comment="会话标题")
    user_id = Column(String(21), nullable=False, index=True, comment="用户ID")
    model_name = Column(
        String(100), nullable=False, default="default", comment="使用的大模型名称"
    )
    is_active = Column(Boolean, default=True, comment="是否激活（未关闭）")
    remark = Column(String(500), nullable=True, comment="备注/扩展信息")


class ChatMessage(AppBaseModel):
    __tablename__ = "chat_messages"
    conversation_id = Column(String(21), nullable=False, index=True, comment="会话ID")
    role = Column(String(20), nullable=False, comment="消息角色：user/assistant/system")
    content = Column(Text, nullable=False, comment="消息内容")
    model_name = Column(String(100), nullable=True, comment="该条消息使用的模型")
    prompt_tokens = Column(Integer, default=0, comment="输入token数")
    completion_tokens = Column(Integer, default=0, comment="输出token数")
    total_tokens = Column(Integer, default=0, comment="总token数")


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_tables())
