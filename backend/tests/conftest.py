"""pytest 公共夹具。

用法：
    cd backend
    python -m pytest tests -v            # 全量
    python -m pytest tests/test_smoke.py # 只跑 API 冒烟（需先启动后端）

约定：
- API 冒烟测试需要后端已在 http://127.0.0.1:8001 运行，未运行时自动 skip（不误报失败）。
- 视觉测试直接调用推理引擎，不依赖 HTTP，但需要模型文件；模型缺失时自动 skip。
"""
import os
import socket

import pytest

BASE_URL = os.getenv("AGRIEYE_TEST_BASE", "http://127.0.0.1:8001")


def _port_open(host: str = "127.0.0.1", port: int = 8001, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _post_login(username: str, password: str):
    import httpx
    r = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password},
        timeout=15.0,
    )
    r.raise_for_status()
    return r.json()


@pytest.fixture(scope="session")
def api_ready():
    if not _port_open():
        pytest.skip("后端未运行（127.0.0.1:8001），跳过 API 冒烟测试")
    return BASE_URL


@pytest.fixture(scope="session")
def admin_token(api_ready):
    """默认演示账号的令牌；账号不存在时跳过。"""
    try:
        return _post_login("admin", "123456")["access_token"]
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"无法登录演示账号（后端是否已初始化？）：{e}")


@pytest.fixture(scope="session")
def second_user(api_ready):
    """注册一个临时二号用户，用于越权用例。"""
    import httpx
    import uuid
    username = f"t_{uuid.uuid4().hex[:8]}"
    try:
        data = httpx.post(
            f"{BASE_URL}/api/auth/register",
            json={"username": username, "password": "Test@12345"},
            timeout=15.0,
        ).json()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"无法注册临时用户：{e}")
    return {"username": username, "token": data["access_token"], "id": data["user"]["id"]}


@pytest.fixture(scope="session")
def engine():
    """推理引擎单例（加载两个 ONNX 模型，较慢，故为 session 级）。"""
    from app.core.model_inference import inference_engine
    try:
        inference_engine.load()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"推理引擎不可用（模型文件缺失？）：{e}")
    return inference_engine
