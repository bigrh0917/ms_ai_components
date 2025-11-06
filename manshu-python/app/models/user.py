"""
用户模型
"""
from sqlalchemy import Column, String, Boolean, DateTime, BigInteger, Enum
from sqlalchemy.sql import func
from app.models.base import Base
import enum


class UserRole(enum.Enum):
    """用户角色枚举"""
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    """用户表"""
    
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='用户唯一标识')
    username = Column(String(255), unique=True, nullable=False, index=True, comment='用户名，唯一')
    email = Column(String(255), unique=True, nullable=False, index=True, comment='邮箱，唯一')
    password = Column(String(255), nullable=False, comment='加密后的密码')
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER, comment='用户角色')
    org_tags = Column(String(255), nullable=True, comment='用户所属组织标签，多个用逗号分隔')
    primary_org = Column(String(50), nullable=True, comment='用户主组织标签')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 打印用户信息
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role.value})>"

