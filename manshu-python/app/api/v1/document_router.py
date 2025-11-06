"""
文档检索和管理接口
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.search_service import search_service
from app.schemas.search import (
    HybridSearchRequest,
    HybridSearchResponse,
    SearchResultItem
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/ping")
async def document_ping():
    """文档模块健康检查"""
    return {"module": "document", "status": "ok"}


@router.get("/search/hybrid", response_model=HybridSearchResponse, summary="混合检索接口")
async def hybrid_search(
    query: str = Query(..., description="搜索查询字符串", min_length=1, max_length=500),
    topK: int = Query(default=10, description="返回结果数量", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    混合检索接口
    
    - 结合语义检索（向量相似度）和关键词检索（全文搜索）
    - 自动应用权限过滤（用户只能看到有权限的文档）
    - 支持指定返回结果数量
    
    Args:
        query: 搜索查询字符串
        topK: 返回结果数量（默认10，最大100）
        db: 数据库会话
        current_user: 当前登录用户
        
    Returns:
        检索结果列表，包含：
        - file_md5: 文件MD5
        - chunk_id: 分块ID
        - text_content: 文本内容
        - score: 相关性分数
        - file_name: 文件名
    """
    try:
        logger.info(f"用户 {current_user.id} 执行混合检索: query='{query[:50]}...', topK={topK}")
        
        # 执行混合检索
        results = await search_service.hybrid_search(
            db=db,
            user=current_user,
            query_text=query,
            top_k=topK
        )
        
        # 转换为响应格式
        result_items = [
            SearchResultItem(
                file_md5=item["file_md5"],
                chunk_id=item["chunk_id"],
                text_content=item["text_content"],
                score=item["score"],
                file_name=item["file_name"]
            )
            for item in results
        ]
        
        return HybridSearchResponse(
            code=200,
            message="检索成功",
            data=result_items
        )
        
    except Exception as e:
        logger.error(f"混合检索失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检索失败: {str(e)}"
        )


