"""
检索相关 Schema
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.schemas.base import BaseResponse


# ========== 混合检索请求 ==========
class HybridSearchRequest(BaseModel):
    """混合检索请求参数"""
    query: str = Field(..., description="搜索查询字符串", min_length=1, max_length=500)
    topK: int = Field(default=10, description="返回结果数量", ge=1, le=100)


# ========== 检索结果 ==========
class SearchResultItem(BaseModel):
    """单个检索结果"""
    file_md5: str = Field(..., description="文件MD5指纹")
    chunk_id: int = Field(..., description="文本分块序号")
    text_content: str = Field(..., description="原始文本内容")
    score: float = Field(..., description="相关性分数")
    file_name: str = Field(..., description="文件名")


# ========== 混合检索响应 ==========
class HybridSearchResponse(BaseResponse[List[SearchResultItem]]):
    """混合检索响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("检索成功", description="提示信息")


# ========== 文档删除响应 ==========
class DocumentDeleteResponse(BaseResponse[Optional[Dict[str, Any]]]):
    """文档删除响应（已废弃，请使用 DeleteFileResponse）"""
    code: int = Field(200, description="状态码")
    message: str = Field("文档删除成功", description="提示信息")

