"""企业级中间件 - 请求日志、耗时统计、简单限流。"""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from loguru import logger


class RequestLogMiddleware(BaseHTTPMiddleware):
    """记录每个请求的方法、路径、状态码、耗时。"""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        cost = (time.perf_counter() - start) * 1000
        # 跳过静态资源与 docs
        path = request.url.path
        if path.startswith(("/uploads", "/openapi", "/docs", "/redoc")):
            return response
        logger.info(
            f"{request.method} {path} -> {response.status_code} ({cost:.1f}ms)"
        )
        response.headers["X-Response-Time"] = f"{cost:.1f}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简易滑动窗口限流（每 IP 每分钟上限），保护识别等重接口。"""

    def __init__(self, app, limit: int = 200, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # 仅对写接口限流
        if request.method in ("POST", "PUT", "DELETE") and path.startswith("/api"):
            client = request.client.host if request.client else "unknown"
            now = time.time()
            q = self._hits[client]
            while q and q[0] < now - self.window:
                q.popleft()
            # 清理过期或空闲 IP 条目，避免长期运行内存泄漏
            if len(self._hits) > 1000:
                stale = [ip for ip, dq in self._hits.items() if not dq or dq[-1] < now - self.window]
                for ip in stale:
                    del self._hits[ip]
            if len(q) >= self.limit:
                logger.warning(f"限流触发：{client} {path}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "请求过于频繁，请稍后再试"},
                )
            q.append(now)
        return await call_next(request)