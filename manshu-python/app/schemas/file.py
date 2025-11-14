"""
文件相关 Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.base import BaseResponse


# ========== 分片上传 ==========
class ChunkUploadResponse(BaseResponse[Dict[str, Any]]):
    """分片上传响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("分片上传成功", description="提示信息")


class ChunkUploadData(BaseModel):
    """分片上传数据"""
    uploaded: List[int] = Field(..., description="已上传的分片索引列表")
    progress: float = Field(..., description="上传进度（百分比）")


# ========== 查询上传状态 ==========
class UploadStatusResponse(BaseResponse[Dict[str, Any]]):
    """查询上传状态响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Success", description="提示信息")


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


class MergeFileResponse(BaseResponse[Dict[str, Any]]):
    """文件合并响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("File merged successfully", description="提示信息")


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


class FileListResponse(BaseResponse[List[FileInfo]]):
    """文件列表响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取文件列表成功", description="提示信息")


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


class FileUploadListResponse(BaseResponse[List[FileUploadInfo]]):
    """用户上传文件列表响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取文件列表成功", description="提示信息")


# ========== 文件删除 ==========
class DeleteFileResponse(BaseResponse[Optional[Dict[str, Any]]]):
    """文件删除响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("文档删除成功", description="提示信息")

