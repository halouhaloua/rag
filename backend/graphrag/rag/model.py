from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func

from app.base_model import BaseModel


class KnowledgeBase(BaseModel):
    __tablename__ = "rag_knowledge_base"

    name = Column(String(200), unique=True, nullable=False, comment="知识库名称")
    description = Column(Text, nullable=True, comment="描述")
    kb_type = Column(String(20), default="user", comment="类型: user/demo")


class KnowledgeBaseFile(BaseModel):
    __tablename__ = "rag_knowledge_base_file"

    kb_id = Column(
        String(21),
        ForeignKey("rag_knowledge_base.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )
    filename = Column(String(255), nullable=False, comment="文件名")
    content = Column(Text, nullable=False, comment="文本内容")
    file_type = Column(String(20), nullable=True, comment="文件类型")
    file_size = Column(Integer, default=0, comment="文件大小(字节)")
    schema_json = Column(JSON, nullable=True, comment="该文件的自定义Schema定义")
    has_graph = Column(Boolean, default=False, comment="是否已构建图谱")


class KnowledgeGraph(BaseModel):
    __tablename__ = "rag_knowledge_graph"

    file_id = Column(
        String(21),
        ForeignKey("rag_knowledge_base_file.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="所属文件",
    )
    graph_data = Column(JSON, nullable=True, comment="图谱结构数据(节点+边)")
    chunks_data = Column(JSON, nullable=True, comment="文本块数据 {chunk_id: text}")
    built_at = Column(DateTime, server_default=func.now(), comment="构建时间")
