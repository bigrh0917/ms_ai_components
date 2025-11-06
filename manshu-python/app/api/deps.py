"""
依赖注入
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.clients.db_client import db_client
from app.utils import jwt_utils
from app.models.user import User

# HTTP Bearer 认证
security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async for session in db_client.get_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前登录用户（使用新的 JWT 工具）"""
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 验证 token（优先查 Redis 缓存，再验证签名）
    if not await jwt_utils.validate_token(token):
        raise credentials_exception
    
    # 从 token 中提取用户名
    username = jwt_utils.extract_username(token)
    if username is None:
        raise credentials_exception
    
    # 查询用户
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user

