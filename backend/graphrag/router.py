# FastAPI imports
from fastapi import APIRouter



# Import routers
from graphrag.rag.api import router as rag_router, ws_router as rag_ws_router
from graphrag.chat.api import router as chat_router
from graphrag.config.api import router as config_router
from graphrag.kb_manager import kb_manager_router

router = APIRouter()

# Include routers
router.include_router(rag_router)
router.include_router(kb_manager_router)
router.include_router(chat_router)
router.include_router(config_router)