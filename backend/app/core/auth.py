"""认证与授权（SEC-002/003/006）

设计要点：
- 密码用 **pbkdf2_sha256 加盐哈希**（passlib 自带盐，纯 Python，无 bcrypt 原生库依赖），
  杜绝明文存储（原实现 `password="123456"` 直接落库）。
- 令牌用 **JWT HS256**（PyJWT）。密钥优先读环境变量 `AGRIEYE_SECRET_KEY`；
  未设置时自动生成并持久化到 `backend/data/.secret_key`，保证重启后旧 token 仍有效，
  且每台部署机器密钥不同（该文件已被 .gitignore 排除）。
- 所有业务接口通过 `CurrentUser` 依赖取用户身份，**不再信任前端传入的 user_id**。
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password, needs_rehash, verify_password  # noqa: F401  re-export
from app.db.database import get_session
from app.db.models import User


# ---------- JWT ----------
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7  # 演示/离线场景：一周内免登录


def _load_secret() -> str:
    env = os.getenv("AGRIEYE_SECRET_KEY")
    if env:
        return env
    key_file = settings.db_path.parent / ".secret_key"
    if key_file.exists():
        try:
            return key_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    key = secrets.token_urlsafe(48)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(key, encoding="utf-8")
    return key


SECRET_KEY = _load_secret()


def create_access_token(user: User) -> tuple[str, int]:
    """返回 (token, 有效秒数)。"""
    expires = timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user.id),
        "username": user.username or "",
        "nickname": user.nickname,
        "role": user.role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + expires,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), int(expires.total_seconds())


# auto_error=False：让“未带 token”也走我们自己的 401 文案，而不是 FastAPI 默认的 403
bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="未登录或登录已过期，请重新登录",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    """解析 Bearer token 并加载用户。任何异常统一返回 401（不回显细节，见 SEC-009）。"""
    if credentials is None or not credentials.credentials:
        raise _CREDENTIALS_EXCEPTION
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise _CREDENTIALS_EXCEPTION
    user = await session.get(User, uid)
    if user is None:
        raise _CREDENTIALS_EXCEPTION
    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """可选认证：带 token 就解析，不带返回 None。用于「登录也能看、不登录也能看」的只读接口。"""
    if credentials is None or not credentials.credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
    return await session.get(User, uid)


# 业务接口统一用这个注解注入当前用户
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def public_user_info(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "role": user.role,
        "region": user.region,
        "avatar": user.avatar,
    }
