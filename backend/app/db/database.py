"""异步 SQLite 数据库引擎与会话管理。"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def init_db() -> None:
    """建表（首次启动自动创建），并初始化默认管理员账号。"""
    from app.db import models  # noqa: F401  确保模型被导入
    from app.db.models import User
    from sqlalchemy import select
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 初始化默认演示账号 admin/123456（仅首次创建；口令以加盐哈希入库，SEC-006）
    from app.core.security import hash_password
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(
            select(User).where(User.username == "admin")
        )).scalars().first()
        if not existing:
            session.add(User(username="admin", password=hash_password("123456"),
                             role="admin", nickname="管理员"))
            await session.commit()
        elif existing.password == "123456":
            # 旧库遗留的明文口令：启动时自动升级为哈希
            existing.password = hash_password("123456")
            session.add(existing)
            await session.commit()


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session