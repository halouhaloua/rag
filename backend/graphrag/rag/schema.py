import warnings
from typing import List, Dict, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

warnings.filterwarnings("ignore", message="Field name \"schema_json\" in \"KnowledgeBaseFile.*")


# ─── 知识库 ───
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(None, description="描述")


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(None, description="描述")


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    kb_type: str = "user"
    file_count: int = 0
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class KnowledgeBaseListResponse(BaseModel):
    items: List[KnowledgeBaseResponse]
    total: int


# ─── 文件 ───
class KnowledgeBaseFileResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: Optional[str] = None
    file_size: int = 0
    has_graph: bool = False
    schema_json: Optional[dict] = None
    sys_create_datetime: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class KnowledgeBaseFileListResponse(BaseModel):
    items: List[KnowledgeBaseFileResponse]
    total: int


class KnowledgeBaseFileCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    kb_id: str
    filename: str
    content: str
    file_type: Optional[str] = None
    file_size: int = 0
    schema_json: Optional[dict] = None
    has_graph: bool = False


class KnowledgeGraphCreate(BaseModel):
    file_id: str
    graph_data: Optional[dict] = None
    chunks_data: Optional[dict] = None


class FileSchemaUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    schema_definition: dict = Field(..., alias="schema", description="Schema定义: {Nodes:[], Relations:[], Attributes:[]}")


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    file_type: Optional[str] = None
    file_size: int = 0
    has_graph: bool = False


class FileUploadResponseWrapper(BaseModel):
    items: List[FileUploadResponse]


# ─── 图谱构建 ───
class ConstructGraphResponse(BaseModel):
    success: bool
    message: str
    graph_data: Optional[Dict] = None


# ─── 提问 ───
class QuestionRequest(BaseModel):
    question: str = Field(..., description="问题")
    file_id: str = Field(..., description="目标文件ID")


class QuestionResponse(BaseModel):
    answer: str
    sub_questions: List[Dict] = []
    retrieved_triples: List[str] = []
    retrieved_chunks: List[str] = []
    reasoning_steps: List[Dict] = []
    visualization_data: Dict = {}


# ─── 删除响应 ───
class DeleteResponse(BaseModel):
    msg: str = "删除成功"
