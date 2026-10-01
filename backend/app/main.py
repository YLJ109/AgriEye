"""FastAPI 应用入口 - 装配所有路由、中间件、生命周期事件。"""
from contextlib import asynccontextmanager
from loguru import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.database import init_db
from app.api import recognize, rag, history, farming, system, chat
from app.core.middleware import RequestLogMiddleware, RateLimitMiddleware
from app.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库与模型缓存。"""
    logger.info(f"启动 {settings.app_name} ...")
    await init_db()
    logger.info("数据库初始化完成")
    # 预热推理引擎（懒加载在首次调用时也可，这里预热便于演示）
    try:
        from app.core.model_inference import inference_engine
        inference_engine.load()
        logger.info("YOLOv8-lite 推理引擎已就绪")
    except Exception as e:  # 模型未训练时仍允许服务启动
        logger.warning(f"推理引擎未就绪（可后续训练后加载）：{e}")
    try:
        from app.core.rag_engine import rag_engine
        rag_engine.load()
        logger.info("RAG 知识库引擎已就绪")
    except Exception as e:
        logger.warning(f"RAG 引擎未就绪：{e}")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="基于多模态小样本的农作物病虫害+缺肥智能诊断与农事 AI 顾问系统",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(RateLimitMiddleware, limit=200, window=60)

# 统一异常处理
register_exception_handlers(app)

# 静态资源（上传图片访问）
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

# 路由注册
app.include_router(system.router, prefix="/api/system", tags=["系统"])
app.include_router(recognize.router, prefix="/api/recognize", tags=["识别"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG 问答"])
app.include_router(farming.router, prefix="/api/farming", tags=["农事建议"])
app.include_router(history.router, prefix="/api/history", tags=["历史记录"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI 对话"])


@app.get("/")
async def root():
    return {"app": settings.app_name, "version": "1.0.0", "docs": "/docs"}