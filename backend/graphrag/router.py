# FastAPI imports
from fastapi import APIRouter



# Import routers
from graphrag.rag.api import router as rag_router
from graphrag.retrieval.api import router as chat_router
from graphrag.config.api import router as config_router

router = APIRouter()

# Include routers
router.include_router(rag_router)
router.include_router(chat_router)
router.include_router(config_router)