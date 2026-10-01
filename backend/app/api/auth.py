"""认证路由（SEC-002 / SEC-006）

对外只暴露三个动作：登录、注册、查询当前身份。
登录成功后返回的 JWT 由前端 axios 拦截器统一携带，业务接口不再接受前端传入的 user_id。
"""
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from loguru import logger

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    hash_password,
    needs_rehash,
    public_user_info,
    verify_password,
    CurrentUser,
)
from app.db.database import get_session
from app.db.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["认证"])

# ---------- 登录失败限流：同用户名 5 次 / 5 分钟（SEC-006 加固，防口令爆破）----------
_FAIL_WINDOW = timedelta(minutes=5)
_FAIL_LIMIT = 5
_fail_log: dict[str, deque[datetime]] = defaultdict(deque)


def _too_many_failures(username: str) -> bool:
    now = datetime.now(timezone.utc)
    q = _fail_log[username]
    while q and now - q[0] > _FAIL_WINDOW:
        q.popleft()
    return len(q) >= _FAIL_LIMIT


def _record_failure(username: str) -> None:
    _fail_log[username].append(datetime.now(timezone.utc))


def _issue(user: User) -> TokenOut:
    token, expires_in = create_access_token(user)
    return TokenOut(
        access_token=token,
        expires_in=expires_in,
        user=UserOut(**public_user_info(user)),
    )


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    if _too_many_failures(payload.username):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "登录失败次数过多，请 5 分钟后再试")

    user = (await session.execute(
        select(User).where(User.username == payload.username)
    )).scalars().first()

    if user is None or not verify_password(payload.password, user.password):
        _record_failure(payload.username)
        # 不区分“用户不存在”与“密码错误”，避免账号枚举
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    # 平滑升级：库中若还是历史明文口令，登录成功后改写为加盐哈希
    if needs_rehash(user.password):
        user.password = hash_password(payload.password)
        session.add(user)
        await session.commit()

    _fail_log.pop(payload.username, None)
    logger.info(f"用户登录成功：{payload.username}（id={user.id}）")
    return _issue(user)


@router.post("/register", response_model=TokenOut)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)):
    exists = (await session.execute(
        select(User).where(User.username == payload.username)
    )).scalars().first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "该用户名已被注册")

    user = User(
        username=payload.username,
        password=hash_password(payload.password),   # 加盐哈希入库，绝不存明文
        nickname=payload.nickname or payload.username,
        region=payload.region,
        role="user",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info(f"新用户注册：{payload.username}（id={user.id}）")
    return _issue(user)


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser):
    return UserOut(**public_user_info(current_user))


@router.post("/logout")
async def logout(current_user: CurrentUser):
    """JWT 无状态，服务端无需回收；这里仅作显式语义，前端清除本地 token 即可。"""
    return {"ok": True}
