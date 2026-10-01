"""口令安全（SEC-006）——独立模块，供 auth / database 共用，避免循环导入。

选用 pbkdf2_sha256：
- passlib 自动带随机盐，同一明文两次哈希结果不同，彩虹表失效；
- 纯 Python 实现，不依赖 bcrypt 原生扩展（Windows 离线部署零编译风险）；
- 历史明文口令通过 `verify_password` 的等值回退 + `needs_rehash` 平滑升级。
"""
import secrets

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

_HASH_PREFIX = "$pbkdf2-sha256$"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    if hashed.startswith(_HASH_PREFIX):
        return bool(pwd_context.verify(plain, hashed))
    # 库中仍是历史明文口令：走一次等值比较，登录成功后由调用方升级为哈希
    return secrets.compare_digest(plain, hashed)


def needs_rehash(hashed: str | None) -> bool:
    """口令是否还是明文/旧格式。"""
    return not bool(hashed) or not hashed.startswith(_HASH_PREFIX)
