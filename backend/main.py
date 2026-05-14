from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from utils.redis import RedisClient
from core.router import router as core_router
from scheduler.router import router as scheduler_router
from core.websocket.router import router as websocket_router
from graphrag.router import router as rag_router
from graphrag.rag.api import ws_router as rag_ws_router

from utils.auth_middleware import AuthMiddleware

# 全局OAuth2方案，用于Swagger显示小锁图标
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/core/auth/login/oauth2", auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    # 初始化演示知识库
    try:
        from scripts.seed_demo_kb import seed_demo_kb
        await seed_demo_kb()
    except Exception as e:
        print(f"Warning: Failed to seed demo KB: {e}")
    # 启动定时任务调度器 (APScheduler 4.x)
    if getattr(settings, 'ENABLE_SCHEDULER', True):
        from apscheduler import AsyncScheduler
        from scheduler.service import scheduler_service
        
        scheduler = AsyncScheduler()
        async with scheduler:
            await scheduler.start_in_background()
            scheduler_service.set_scheduler(scheduler)
            app.state.scheduler = scheduler
            
            # 加载数据库中的任务
            await scheduler_service.load_jobs_from_db()
            
            yield
            
            # 关闭时
            scheduler_service.set_running(False)
    else:
        yield
    
    await RedisClient.close()

app = FastAPI(
    title=settings.APP_NAME,
    description="一个简单的FastAPI CRUD示例",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
    },
)

# 添加全局认证中间件（白名单内的路由无需认证）
app.add_middleware(AuthMiddleware)

# 注册路由（带全局OAuth2依赖，用于Swagger显示小锁图标）
app.include_router(core_router, prefix="/api/core", dependencies=[Depends(oauth2_scheme)])
app.include_router(scheduler_router, prefix="/api", dependencies=[Depends(oauth2_scheme)])
app.include_router(rag_router, prefix="/rag", dependencies=[Depends(oauth2_scheme)])
app.include_router(rag_ws_router, prefix="/rag")
# WebSocket路由（不需要OAuth2依赖，WebSocket自己处理认证）
app.include_router(websocket_router)


@app.get("/", tags=["根路径"])
async def root():
    """API根路径"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "env": settings.ENV,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
