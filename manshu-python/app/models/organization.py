"""
组织标签模型
"""
from sqlalchemy import Column, String, Text, BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class OrganizationTag(Base):
    """组织标签表"""
    
    __tablename__ = "organization_tags"
    
    tag_id = Column(String(50), primary_key=True, comment='标签唯一标识')
    name = Column(String(100), nullable=False, comment='标签名称')
    description = Column(Text, comment='描述')
    parent_tag = Column(String(50), ForeignKey('organization_tags.tag_id', ondelete='SET NULL', onupdate='CASCADE'), comment='父标签ID')
    created_by = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='创建者ID')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 关系
    parent = relationship("OrganizationTag", remote_side=[tag_id], backref="children")
    creator = relationship("User", backref="created_tags")
    
    def __repr__(self):
        return f"<OrganizationTag(tag_id={self.tag_id}, name={self.name})>"

    # 可选索引（如常用按 name 查找，可添加）
    __table_args__ = (
        Index('idx_org_tag_name', 'name'),
    )

