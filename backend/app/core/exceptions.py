"""统一异常处理 - 把各类异常转为一致的 JSON 错误响应。"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"参数校验失败 {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数校验失败",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception):
        logger.exception(f"未处理异常 {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误，请稍后重试",
                "detail": str(exc),
            },
        )