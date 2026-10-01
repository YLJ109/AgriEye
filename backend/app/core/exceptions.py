"""统一异常处理 - 把各类异常转为一致的 JSON 错误响应。

SEC-009：不再把 `str(exc)` 回显给客户端（可能泄露文件路径、SQL、密钥片段），
改为返回 traceId；客户端报 traceId，服务端日志里按 traceId 定位完整栈。
REL-001：每个失败响应都带 traceId，可与中间件请求日志串联排查。
"""
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings


def _new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        trace_id = _new_trace_id()
        logger.warning(f"[{trace_id}] 参数校验失败 {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数校验失败",
                # 字段级错误对调用方有调试价值，且不含内部实现细节，予以保留
                "errors": exc.errors(),
                "trace_id": trace_id,
            },
        )

    @app.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception):
        trace_id = _new_trace_id()
        logger.exception(f"[{trace_id}] 未处理异常 {request.url.path}: {exc}")
        content: dict = {
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "trace_id": trace_id,
        }
        # 仅调试模式回显异常细节
        if settings.debug:
            content["detail"] = f"{type(exc).__name__}: {exc}"
        return JSONResponse(status_code=500, content=content)
