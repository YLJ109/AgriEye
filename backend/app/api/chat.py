"""AI 对话路由 - 智谱 GLM 大模型 API 转发（支持流式输出）。"""
import httpx
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from app.config import settings

router = APIRouter()

ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_TEXT_MODEL = "glm-4-flash"
DEFAULT_VISION_MODEL = "glm-4v-flash"
SYSTEM_PROMPT = (
    "你是「智农慧眼」AI 农事顾问，精通农作物病虫害防治、施肥管理、农事安排。"
    "请用专业、简洁、实用的中文回答农业问题，给出具体可操作的建议。"
    "如涉及用药，请注明药剂名称、稀释倍数和安全间隔期。"
    "回答内容请使用 Markdown 格式，包含标题、列表、加粗等格式以提升可读性。"
)


class ChatMessage(BaseModel):
    role: str
    content: str | list


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    api_key: str
    image_base64: str | None = None
    temperature: float = 0.7
    stream: bool = False


def _build_payload(req: ChatRequest) -> tuple[dict, list]:
    model = req.model or (DEFAULT_VISION_MODEL if req.image_base64 else DEFAULT_TEXT_MODEL)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in req.messages:
        messages.append({"role": m.role, "content": m.content})
    if req.image_base64:
        last = messages[-1]
        last["content"] = [
            {"type": "text", "text": last["content"] if isinstance(last["content"], str) else "请分析这张图片"},
            {"type": "image_url", "image_url": {"url": req.image_base64}},
        ]
    payload = {"model": model, "messages": messages, "temperature": req.temperature, "stream": req.stream}
    headers = {"Authorization": f"Bearer {req.api_key}", "Content-Type": "application/json"}
    return payload, headers


def _parse_sse(text: str) -> str:
    """解析智谱 SSE 流式响应文本，拼接出完整回答。"""
    content = ""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            delta = json.loads(data).get("choices", [{}])[0].get("delta", {})
            if "content" in delta:
                content += delta["content"]
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
    return content


DIRECT_FIRST = [(False, 8.0), (True, 20.0)]   # 直连优先，代理兜底
PROXY_FIRST = [(True, 20.0), (False, 8.0)]    # 代理优先，直连兜底


async def _fetch(payload: dict, headers: dict, modes=DIRECT_FIRST) -> tuple[int, str]:
    """向智谱发请求，返回 (状态码, 响应全文)。响应在 client 上下文内读完，避免流式生命周期问题。

    为什么会绕开环境代理：本机 HTTPS_PROXY 指向随会话变化的本地端口（127.0.0.1:586xx，
    多开会话时会同时存在 58604/58608/58635 等多个），后端进程常继承到上一次会话的旧端口。
    实测经该链路转发智谱时耗时 20~30s 且约一半请求以 502 结束；直连本机已验证可行，故放首位。
    """
    last_err = None
    for trust_env, connect_to in modes:
        way = "环境代理" if trust_env else "直连"
        try:
            timeout = httpx.Timeout(60.0, connect=connect_to)
            async with httpx.AsyncClient(timeout=timeout, trust_env=trust_env) as client:
                request = client.build_request("POST", ZHIPU_URL, json=payload, headers=headers)
                resp = await client.send(request, stream=True)
                await resp.aread()
                return resp.status_code, resp.text
        except (httpx.RequestError, httpx.TimeoutException) as e:
            last_err = e
            logger.warning(f"智谱请求失败（{way}）：{type(e).__name__}: {e}")
    raise last_err


def _upstream_error(status: int, body: str) -> HTTPException:
    """按上游状态码精确映射，避免把所有问题都报成误导性的 502。"""
    body = (body or "")[:300]
    logger.error(f"智谱上游异常 status={status} body={body}")
    if status in (401, 403):
        return HTTPException(401, "API Key 无效或已过期，请在「API 设置」中重新填写后重试")
    if status == 429:
        return HTTPException(429, "智谱 API 请求过于频繁，请稍后再试")
    if status == 400:
        return HTTPException(400, f"智谱 API 请求有误（模型名或参数不合法）：{body}")
    if 400 <= status < 500:
        return HTTPException(400, f"智谱 API 请求有误（{status}）：{body}")
    return HTTPException(502, f"智谱服务暂时异常（{status}）：{body}")


@router.post("/completions")
async def chat_completions(req: ChatRequest):
    """转发到智谱 GLM API，支持纯文字、图片理解和流式输出。

    密钥来源优先级：请求体 > 服务端环境变量 ZHIPU_API_KEY。
    服务端配置后，浏览器侧无需保存明文 Key（SEC-005 的推荐用法）。
    """
    server_key = (settings.zhipu_api_key or "").strip()
    if not req.api_key and server_key:
        req.api_key = server_key
    if not req.api_key:
        raise HTTPException(400, "请先配置 API Key（前端设置，或服务端环境变量 ZHIPU_API_KEY）")
    payload, headers = _build_payload(req)
    try:
        status, text = await _fetch(payload, headers)
        if status >= 500:
            # 上游 5xx 常是链路问题（实测约一半请求会 502）：换另一条链路重试一次
            logger.warning(f"智谱上游 {status}，切换链路重试")
            status, text = await _fetch(payload, headers, PROXY_FIRST)
        if status >= 400:
            raise _upstream_error(status, text)
        if req.stream:
            return {"content": _parse_sse(text), "model": payload["model"], "stream": True}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 常见于被网络代理拦截：返回 200 却是个 HTML/文本错误页
            raise HTTPException(502, f"智谱返回了非 JSON 响应（多半被网络代理拦截）：{text[:200]}")
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise HTTPException(502, f"智谱响应格式异常：{text[:200]}")
        return {"content": content, "model": payload["model"], "stream": False}
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(504, "请求智谱 API 超时，请检查网络或稍后重试")
    except httpx.RequestError as e:
        raise HTTPException(503, f"无法连接智谱 API（直连与环境代理均失败）：{type(e).__name__}: {e}")
    except Exception as e:
        logger.exception("请求智谱 API 出现未预期错误")
        raise HTTPException(502, f"请求智谱 API 失败：{type(e).__name__}: {e}")


@router.get("/models")
async def list_models():
    """返回推荐的智谱免费模型列表。"""
    return {
        "models": [
            {"id": "glm-4-flash", "label": "GLM-4-Flash（文字·免费）", "type": "text"},
            {"id": "glm-4v-flash", "label": "GLM-4V-Flash（图片理解·免费）", "type": "vision"},
            {"id": "glm-4-plus", "label": "GLM-4-Plus（文字·高级）", "type": "text"},
            {"id": "glm-4v-plus", "label": "GLM-4V-Plus（图片理解·高级）", "type": "vision"},
        ]
    }