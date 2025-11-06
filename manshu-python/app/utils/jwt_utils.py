"""
JWT 工具（精简版）
- Base64/原始密钥兼容
- Access Token：写入 tokenId/role/userId/sub 及可选 orgTags/primaryOrg
- Redis 缓存校验（优先缓存，再验签）
- 临时令牌（图形/邮箱链路）
"""
from __future__ import annotations

from typing import Any, Optional, Dict
from datetime import datetime, timedelta, timezone
import base64
import json

from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.clients.redis_client import redis_client
from app.models.user import User
from app.utils.security import generate_uuid


# 访问令牌过期（毫秒）
EXPIRATION_TIME_MS = 60 * 60 * 1000  # 1h


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _get_signing_key() -> bytes | str:
    """优先尝试 Base64 解码 SECRET_KEY，失败则使用原始字符串。"""
    raw = settings.SECRET_KEY
    try:
        return base64.b64decode(raw)
    except Exception:
        return raw




async def _cache_token(token_id: str, user_id: str, username: str, expire_at_ms: int) -> None:
    ttl_sec = max(1, (expire_at_ms - _now_ms()) // 1000)
    payload = {"userId": user_id, "username": username, "expireAt": expire_at_ms}
    await redis_client.set(f"token:{token_id}", json.dumps(payload), expire=ttl_sec)
    # 索引用户持有 token 集合，便于批量失效
    # 采用 set 存储，设置同样 TTL（近似处理）
    await redis_client.set(f"user_tokens:{user_id}:{token_id}", "1", expire=ttl_sec)


def _encode_jwt(claims: Dict[str, Any]) -> str:
    return jwt.encode(claims, _get_signing_key(), algorithm=settings.ALGORITHM)


def _decode_jwt(token: str, verify_exp: bool = True) -> Optional[Dict[str, Any]]:
    try:
        options = None if verify_exp else {"verify_exp": False}
        return jwt.decode(token, _get_signing_key(), algorithms=[settings.ALGORITHM], options=options)
    except JWTError:
        return None


# ========= 临时令牌（图形/邮箱验证链路） =========
def create_temp_token(email: str) -> str:
    """创建临时令牌（短期使用）。"""
    data = {
        "sub": email,
        "type": "temp",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.TEMP_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return _encode_jwt(data)


def verify_temp_token(token: str) -> Optional[str]:
    """验证临时令牌，返回 email；失败返回 None。"""
    payload = _decode_jwt(token, verify_exp=True)
    if not payload or payload.get("type") != "temp":
        return None
    return payload.get("sub")


async def generate_token(db: AsyncSession, username: str) -> str:
    """生成 Access Token 并缓存到 Redis。"""
    result = await db.execute(select(User).where(User.username == username))
    user: Optional[User] = result.scalar_one_or_none()
    if not user:
        raise RuntimeError("User not found")

    token_id = generate_uuid().replace("-", "")
    now = datetime.now(timezone.utc)
    expire_at = now + timedelta(milliseconds=EXPIRATION_TIME_MS)
    expire_at_ms = int(expire_at.timestamp() * 1000)

    claims: Dict[str, Any] = {
        "tokenId": token_id,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "userId": str(user.id),
        "sub": user.username,
        "exp": expire_at,
        "iat": now,
    }
    if getattr(user, "org_tags", None):
        claims["orgTags"] = user.org_tags
    if getattr(user, "primary_org", None):
        claims["primaryOrg"] = user.primary_org

    token = _encode_jwt(claims)
    await _cache_token(token_id, str(user.id), user.username, expire_at_ms)
    return token


async def validate_token(token: str) -> bool:
    """先查缓存有效性，再校验签名与过期。"""
    claims = _decode_jwt(token, verify_exp=False)
    if not claims:
        return False
    token_id = claims.get("tokenId")
    if not token_id:
        return False
    cached = await redis_client.get(f"token:{token_id}")
    if not cached:
        return False
    # 二次验证：签名+过期
    claims2 = _decode_jwt(token, verify_exp=True)
    return claims2 is not None


def extract_username(token: str) -> Optional[str]:
    claims = _decode_jwt(token, verify_exp=False)
    return claims.get("sub") if claims else None


def extract_user_id(token: str) -> Optional[str]:
    claims = _decode_jwt(token, verify_exp=False)
    return claims.get("userId") if claims else None


def extract_role(token: str) -> Optional[str]:
    claims = _decode_jwt(token, verify_exp=False)
    return claims.get("role") if claims else None


def extract_org_tags(token: str) -> Optional[str]:
    claims = _decode_jwt(token, verify_exp=False)
    return claims.get("orgTags") if claims else None


def extract_primary_org(token: str) -> Optional[str]:
    claims = _decode_jwt(token, verify_exp=False)
    return claims.get("primaryOrg") if claims else None


async def invalidate_token(token: str) -> None:
    claims = _decode_jwt(token, verify_exp=False)
    if not claims:
        return
    token_id = claims.get("tokenId")
    user_id = claims.get("userId")
    exp = claims.get("exp")
    if not token_id or not user_id or not exp:
        return
    # 删除缓存并加入黑名单（简单实现：删除缓存为主）
    await redis_client.delete(f"token:{token_id}")
    # 移除 user 索引
    await redis_client.delete(f"user_tokens:{user_id}:{token_id}")


    # 其余刷新/失效批量逻辑按需扩展


