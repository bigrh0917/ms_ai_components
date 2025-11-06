"""
聊天相关模型
"""
from sqlalchemy import Column, String, BigInteger, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class ConversationArchive(Base):
    """会话归档表"""
    
    __tablename__ = "conversation_archive"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键')
    conversation_id = Column(String(36), unique=True, nullable=False, index=True, comment='会话ID（UUID）')
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    archived_at = Column(DateTime, nullable=False, server_default=func.now(), comment='归档时间')
    
    # 关系
    user = relationship("User", backref="archived_conversations")
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ConversationArchive(id={self.id}, conversation_id={self.conversation_id}, user_id={self.user_id})>"
    
    __table_args__ = (
        Index('idx_user_archived', 'user_id', 'archived_at'),
    )


class ConversationMessage(Base):
    """会话消息表"""
    
    __tablename__ = "conversation_messages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键')
    conversation_id = Column(String(36), ForeignKey('conversation_archive.conversation_id', ondelete='CASCADE'), nullable=False, comment='会话ID')
    role = Column(String(20), nullable=False, comment='角色: user 或 assistant')
    content = Column(Text, nullable=False, comment='消息内容')
    timestamp = Column(DateTime, nullable=False, comment='消息时间戳')
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment='创建时间')
    
    # 关系
    conversation = relationship("ConversationArchive", back_populates="messages")
    
    def __repr__(self):
        return f"<ConversationMessage(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"
    
    __table_args__ = (
        Index('idx_conversation_timestamp', 'conversation_id', 'timestamp'),
    )


