"""企业级中间件 - 请求日志、耗时统计、链路 ID、简单限流。"""
import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from loguru import logger

REQUEST_ID_HEADER = "X-Request-ID"


class RequestLogMiddleware(BaseHTTPMiddleware):
    """记录每个请求的方法、路径、状态码、耗时，并注入链路 ID（REL-001）。

    链路 ID 的取值优先级：
    1. 上游（如 Nginx）传来的 X-Request-ID —— 便于跨服务串联
    2. 本次生成的 12 位随机 ID
    它会同时写进日志前缀和响应头，异常处理器也从 request.state 复用同一个值，
    这样「用户报一个 ID」就能 grep 出这一次操作的完整链路。
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        response: Response = await call_next(request)
        cost = (time.perf_counter() - start) * 1000
        # 跳过静态资源与 docs
        path = request.url.path
        if path.startswith(("/uploads", "/preview_tmp", "/openapi", "/docs", "/redoc")):
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        logger.info(
            f"[{request_id}] {request.method} {path} -> {response.status_code} ({cost:.1f}ms)"
        )
        response.headers["X-Response-Time"] = f"{cost:.1f}ms"
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简易滑动窗口限流（每 IP 每分钟上限），保护识别等重接口。"""

    def __init__(self, app, limit: int = 200, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque] = defaultdict(deque)
        self._last_sweep = time.time()

    @staticmethod
    def _client_ip(request: Request) -> str:
        """CONC-002：反向代理后面 request.client.host 全是代理 IP，会误伤全部用户。

        信任链：X-Forwarded-For 最左段（真实客户端）。注意只有在确实部署了会重写
        该头的反向代理时才应信任它，直连部署下没有这个头，自动回退到直连 IP。
        """
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # 仅对写接口限流
        if request.method in ("POST", "PUT", "DELETE") and path.startswith("/api"):
            client = self._client_ip(request)
            now = time.time()
            q = self._hits[client]
            while q and q[0] < now - self.window:
                q.popleft()
            # CONC-002：惰性 TTL 清理。原实现只在条目数 >1000 时才清，
            # 长期运行下 idle IP 的键会一直留在内存里；改为每个窗口扫一次。
            if now - self._last_sweep > self.window:
                self._last_sweep = now
                stale = [ip for ip, dq in self._hits.items()
                         if not dq or dq[-1] < now - self.window]
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