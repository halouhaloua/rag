from fastapi import APIRouter
from pydantic import BaseModel
from graphrag.config import get_config

router = APIRouter(prefix="/api/config", tags=["config"])


class IRCoTRequest(BaseModel):
    enable: bool


@router.get("/ircot")
async def get_ircot_status():
    cfg = get_config()
    return cfg.to_dict_ircot()


@router.post("/ircot")
async def set_ircot_status(req: IRCoTRequest):
    cfg = get_config()
    cfg.set_ircot_enabled(req.enable)
    return {
        "message": f"IRCoT {'enabled' if req.enable else 'disabled'}",
        "enable_ircot": req.enable,
    }
