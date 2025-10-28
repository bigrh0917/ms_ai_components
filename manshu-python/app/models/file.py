"""
文件相关模型
"""
from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime, ForeignKey, SmallInteger, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class FileUpload(Base):
    """文件上传记录表"""
    
    __tablename__ = "file_upload"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键')
    file_md5 = Column(String(32), nullable=False, index=True, comment='文件MD5指纹')
    file_name = Column(String(255), nullable=False, comment='文件名称')
    total_size = Column(BigInteger, nullable=False, comment='文件大小（字节）')
    status = Column(SmallInteger, nullable=False, default=0, comment='上传状态：0=上传中，1=已完成，2=失败')
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    org_tag = Column(String(50), ForeignKey('organization_tags.tag_id', ondelete='SET NULL'), comment='组织标签')
    is_public = Column(Boolean, nullable=False, default=False, comment='是否公开')
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment='创建时间')
    merged_at = Column(DateTime, nullable=True, onupdate=func.now(), comment='合并时间')
    
    # 关系
    user = relationship("User", backref="uploaded_files")
    organization = relationship("OrganizationTag", backref="files")
    chunks = relationship("ChunkInfo", back_populates="file", cascade="all, delete-orphan")
    vectors = relationship("DocumentVector", back_populates="file", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<FileUpload(id={self.id}, file_name={self.file_name}, status={self.status})>"


class ChunkInfo(Base):
    """文件分片信息表"""
    
    __tablename__ = "chunk_info"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键')
    file_md5 = Column(String(32), ForeignKey('file_upload.file_md5', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, comment='文件MD5（外键）')
    chunk_index = Column(Integer, nullable=False, comment='分片序号（0-based）')
    chunk_md5 = Column(String(32), nullable=False, comment='分片MD5校验')
    storage_path = Column(String(255), nullable=False, comment='分片存储路径（如 MinIO URL）')
    
    # 关系
    file = relationship("FileUpload", back_populates="chunks")
    
    def __repr__(self):
        return f"<ChunkInfo(id={self.id}, file_md5={self.file_md5}, chunk_index={self.chunk_index})>"


class DocumentVector(Base):
    """文档向量化结果表"""
    
    __tablename__ = "document_vectors"
    
    vector_id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键，自增ID')
    file_md5 = Column(String(32), ForeignKey('file_upload.file_md5', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, comment='文件指纹（关联file_upload表）')
    chunk_id = Column(Integer, nullable=False, comment='文本分块序号')
    text_content = Column(Text, comment='原始文本内容')
    model_version = Column(String(32), default='all-MiniLM-L6-v2', comment='生成向量所使用的模型版本')
    
    # 关系
    file = relationship("FileUpload", back_populates="vectors")
    
    def __repr__(self):
        return f"<DocumentVector(vector_id={self.vector_id}, file_md5={self.file_md5}, chunk_id={self.chunk_id})>"

