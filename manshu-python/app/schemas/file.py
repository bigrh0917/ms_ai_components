"""
文件相关 Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========== 分片上传 ==========
class ChunkUploadResponse(BaseModel):
    """分片上传响应"""
    code: int = 200
    message: str = "分片上传成功"
    data: dict


class ChunkUploadData(BaseModel):
    """分片上传数据"""
    uploaded: List[int] = Field(..., description="已上传的分片索引列表")
    progress: float = Field(..., description="上传进度（百分比）")


# ========== 查询上传状态 ==========
class UploadStatusResponse(BaseModel):
    """查询上传状态响应"""
    code: int = 200
    message: str = "Success"
    data: dict


class UploadStatusData(BaseModel):
    """上传状态数据"""
    uploaded: List[int] = Field(..., description="已上传的分片索引列表")
    progress: float = Field(..., description="上传进度（百分比）")
    total_chunks: int = Field(..., description="总分片数")


# ========== 文件合并 ==========
class MergeFileRequest(BaseModel):
    """文件合并请求"""
    file_md5: str = Field(..., min_length=32, max_length=32, description="文件MD5值")
    file_name: str = Field(..., min_length=1, description="文件名")


class MergeFileResponse(BaseModel):
    """文件合并响应"""
    code: int = 200
    message: str = "File merged successfully"
    data: dict


class MergeFileData(BaseModel):
    """文件合并数据"""
    object_url: str = Field(..., description="文件访问URL")
    file_size: int = Field(..., description="文件大小（字节）")


# ========== 文件列表 ==========
class FileInfo(BaseModel):
    """文件信息"""
    fileMd5: str
    fileName: str
    totalSize: int
    status: int
    userId: str
    orgTag: Optional[str] = None
    isPublic: bool
    createdAt: datetime
    mergedAt: Optional[datetime] = None


class FileListResponse(BaseModel):
    """文件列表响应"""
    status: str = "success"
    data: List[FileInfo]


class FileUploadInfo(BaseModel):
    """用户上传的文件信息"""
    fileMd5: str
    fileName: str
    totalSize: int
    status: int
    userId: str
    orgTagName: Optional[str] = None
    isPublic: bool
    createdAt: datetime
    mergedAt: Optional[datetime] = None


class FileUploadListResponse(BaseModel):
    """用户上传文件列表响应"""
    status: str = "success"
    data: List[FileUploadInfo]


# ========== 文件删除 ==========
class DeleteFileResponse(BaseModel):
    """文件删除响应"""
    status: str = "success"
    message: str = "文档删除成功"

