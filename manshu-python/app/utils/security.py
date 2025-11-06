"""
安全相关工具函数（仅保留密码哈希与通用 UUID）。
"""
from passlib.context import CryptContext
import uuid

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())

