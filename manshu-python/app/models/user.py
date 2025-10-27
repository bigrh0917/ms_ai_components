"""
用户模型
"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class User(Base):
    """用户表"""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)  # 邮箱验证通过后设为 True
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 打印用户信息
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

