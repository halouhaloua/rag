from typing import List, Optional
from pydantic import BaseModel


class RoleInfo(BaseModel):
    id: str
    name: str
    code: str
    role_type: int = 1
    status: bool = True

    model_config = {"from_attributes": True}


class KBPermissionUpdateRequest(BaseModel):
    kb_ids: List[str]


class KBAccessCheckResponse(BaseModel):
    has_access: bool
