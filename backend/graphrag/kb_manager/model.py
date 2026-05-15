from sqlalchemy import Column, String, ForeignKey, UniqueConstraint

from app.base_model import BaseModel


class KnowledgeBaseRole(BaseModel):
    __tablename__ = "rag_knowledge_base_role"

    role_id = Column(
        String(21),
        ForeignKey("core_role.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="角色ID",
    )
    kb_id = Column(
        String(21),
        ForeignKey("rag_knowledge_base.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="知识库ID",
    )

    __table_args__ = (
        UniqueConstraint("role_id", "kb_id", name="uq_role_kb"),
    )
