"""API 冒烟测试 —— 覆盖 B1/B3/B6 的关键安全与正确性断言。

对应审查项：SEC-002（认证）、SEC-003（越权）、SEC-007（上传魔数）、
FUNC-001（搜索下沉后端）、SEC-009（异常不回显）。
"""
import io
import uuid

import httpx
import pytest

from .conftest import BASE_URL  # noqa: F401  让测试可直接引用


def _png_bytes() -> bytes:
    """最小的合法 PNG（1x1 透明），用于上传接口测试。"""
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000a49444154789c6300010000050001"
        "0d0a2db40000000049454e44ae426082"
    )


# ---------- 公开接口 ----------
def test_health(api_ready):
    assert httpx.get(f"{api_ready}/api/system/health", timeout=10).status_code == 200


def test_system_info(api_ready):
    data = httpx.get(f"{api_ready}/api/system/info", timeout=10).json()
    assert "app_name" in data and "model_loaded" in data


# ---------- SEC-002：未认证一律 401 ----------
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/history/list"),
    ("GET", "/api/system/stats"),
    ("GET", "/api/auth/me"),
    ("DELETE", "/api/history/1"),
    ("GET", "/api/farming/reminders"),
])
def test_unauthenticated_rejected(api_ready, method, path):
    r = httpx.request(method, f"{api_ready}{path}", timeout=10)
    assert r.status_code == 401, f"{method} {path} 应拒绝匿名访问"


def test_forged_token_rejected(api_ready):
    r = httpx.get(
        f"{api_ready}/api/history/list",
        headers={"Authorization": "Bearer forged.token.value"},
        timeout=10,
    )
    assert r.status_code == 401


# ---------- 认证主链路 ----------
def test_login_and_me(api_ready, admin_token):
    me = httpx.get(
        f"{api_ready}/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_wrong_password_rejected(api_ready):
    r = httpx.post(
        f"{api_ready}/api/auth/login",
        json={"username": "admin", "password": "definitely-wrong"},
        timeout=15,
    )
    assert r.status_code == 401


def test_authenticated_history_ok(api_ready, admin_token):
    r = httpx.get(
        f"{api_ready}/api/history/list",
        params={"page": 1, "page_size": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert set(["total", "page", "page_size", "items"]).issubset(body)


# ---------- SEC-003：跨用户越权 ----------
def test_cross_user_cannot_read_others_record(api_ready, admin_token, second_user):
    """二号用户访问 admin 的记录，必须表现为不存在（404），而不是 200 或 403。"""
    listing = httpx.get(
        f"{api_ready}/api/history/list",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    ).json()
    if not listing["items"]:
        pytest.skip("admin 名下暂无记录，无法构造越权场景")
    target_id = listing["items"][0]["id"]

    r = httpx.get(
        f"{api_ready}/api/history/detail/{target_id}",
        headers={"Authorization": f"Bearer {second_user['token']}"},
        timeout=10,
    )
    assert r.status_code == 404, "跨用户读取应被拦截"


def test_cross_user_cannot_delete_others_record(api_ready, admin_token, second_user):
    listing = httpx.get(
        f"{api_ready}/api/history/list",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    ).json()
    if not listing["items"]:
        pytest.skip("admin 名下暂无记录，无法构造越权场景")
    target_id = listing["items"][0]["id"]

    r = httpx.delete(
        f"{api_ready}/api/history/{target_id}",
        headers={"Authorization": f"Bearer {second_user['token']}"},
        timeout=10,
    )
    assert r.status_code == 404, "跨用户删除应被拦截"


# ---------- TEST-001：历史列表分页 ----------
def test_pagination_page_size_is_respected(api_ready, admin_token):
    r = httpx.get(
        f"{api_ready}/api/history/list",
        params={"page": 1, "page_size": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    ).json()
    assert len(r["items"]) <= 1, "page_size 应生效"
    assert r["page"] == 1 and r["page_size"] == 1


def test_pagination_beyond_last_page_is_empty(api_ready, admin_token):
    """翻过最后一页应返回空列表，而不是报错或回退到第一页。"""
    r = httpx.get(
        f"{api_ready}/api/history/list",
        params={"page": 9999, "page_size": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert isinstance(body["total"], int)


# ---------- SEC-007：上传魔数校验 ----------
def test_upload_rejects_fake_image(api_ready, admin_token):
    """扩展名是 .png 但内容不是图片 —— 应被魔数校验拦下。"""
    files = {"file": ("evil.png", io.BytesIO(b"#!/bin/sh\nrm -rf /\n"), "image/png")}
    r = httpx.post(
        f"{api_ready}/api/recognize",
        files=files,
        data={"preview": "true"},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert r.status_code == 400, "伪造扩展名的非图片文件应被拒绝"


def test_upload_rejects_unsupported_extension(api_ready, admin_token):
    files = {"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")}
    r = httpx.post(
        f"{api_ready}/api/recognize",
        files=files,
        data={"preview": "true"},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert r.status_code == 400


# ---------- FUNC-001：搜索下沉后端 ----------
def test_history_search_param_accepted(api_ready, admin_token):
    r = httpx.get(
        f"{api_ready}/api/history/list",
        params={"page": 1, "page_size": 5, "search": "稻瘟病"},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    assert r.status_code == 200
    assert "items" in r.json()


# ---------- FUNC-004：排序下沉到后端 ----------
def test_sort_param_changes_order(api_ready, admin_token):
    def ids(sort):
        r = httpx.get(
            f"{api_ready}/api/history/list",
            params={"page": 1, "page_size": 20, "sort": sort},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        ).json()
        return [i["id"] for i in r["items"]]

    desc_ids, asc_ids = ids("time"), ids("time-asc")
    if len(desc_ids) < 2:
        pytest.skip("样本不足，无法验证排序")
    assert desc_ids == list(reversed(asc_ids)), "时间正序与倒序应互为逆序"
    # 未知排序值不应报错，回退到默认
    assert ids("not-a-sort") == desc_ids


# ---------- DATA-003：预览检测不污染 uploads ----------
def test_preview_does_not_write_uploads(api_ready, admin_token):
    """连续预览检测后，正式 uploads 目录的文件数不应增长。"""
    from app.config import settings
    before = len([p for p in settings.upload_dir.iterdir() if p.is_file()])
    for _ in range(3):
        files = {"file": (f"prev_{uuid.uuid4().hex[:8]}.png", io.BytesIO(_png_bytes()), "image/png")}
        r = httpx.post(
            f"{api_ready}/api/recognize",
            files=files,
            data={"preview": "true"},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code == 200
    after = len([p for p in settings.upload_dir.iterdir() if p.is_file()])
    assert after == before, f"预览检测不应写 uploads（{before} -> {after}）"


# ---------- SEC-009：异常响应不回显内部细节 ----------
def test_error_response_has_no_stack_detail(api_ready):
    """触发一个 422，确认不会泄露内部实现（仅允许字段级 errors + trace_id）。"""
    r = httpx.post(f"{api_ready}/api/auth/login", json={"username": 123}, timeout=10)
    assert r.status_code == 422
    body = r.json()
    assert "trace_id" in body, "失败响应应带 traceId 便于排查（REL-001）"
    assert "Traceback" not in str(body)
