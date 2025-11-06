"""
检索相关 Schema
"""
from pydantic import BaseModel, Field
from typing import List, Optional


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
class HybridSearchResponse(BaseModel):
    """混合检索响应"""
    code: int = 200
    message: str = "检索成功"
    data: List[SearchResultItem] = Field(default_factory=list, description="检索结果列表")


# ========== 文档删除响应 ==========
class DocumentDeleteResponse(BaseModel):
    """文档删除响应"""
    status: str = Field(..., description="状态：success 或 error")
    message: str = Field(..., description="提示信息")

