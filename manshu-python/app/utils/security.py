"""
安全相关工具函数
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.core.config import settings
import uuid

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT access token
    
    Args:
        data: 要编码的数据（通常包含 sub: user_id）
        expires_delta: 过期时间间隔
        
    Returns:
        JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_temp_token(email: str) -> str:
    """
    创建临时令牌（用于验证流程）
    
    Args:
        email: 邮箱地址
        
    Returns:
        临时令牌
    """
    data = {
        "sub": email,
        "type": "temp",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.TEMP_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_temp_token(token: str) -> Optional[str]:
    """
    验证临时令牌
    
    Args:
        token: 临时令牌
        
    Returns:
        邮箱地址，失败返回 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # 检查令牌类型
        if payload.get("type") != "temp":
            return None
        
        email: str = payload.get("sub")
        return email
        
    except JWTError:
        return None


def decode_token(token: str) -> Optional[Dict]:
    """解码 JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())

