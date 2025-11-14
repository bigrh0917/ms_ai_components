"""
文件相关接口路由
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.file import (
    ChunkUploadResponse, ChunkUploadData,
    UploadStatusResponse, UploadStatusData,
    MergeFileRequest, MergeFileResponse, MergeFileData,
    DeleteFileResponse,
    FileListResponse, FileInfo,
    FileUploadListResponse, FileUploadInfo
)
from app.services.file_service import file_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 上传相关路由
upload_router = APIRouter()

@upload_router.post("/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    file: UploadFile = File(...),
    fileMd5: str = Form(...),
    chunkIndex: int = Form(...),
    totalSize: int = Form(...),
    fileName: str = Form(...),
    totalChunks: int = Form(None),
    orgTag: str = Form(None),
    isPublic: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    分片上传接口
    
    - 接收文件分片
    - 验证数据完整性
    - 存储到MinIO临时目录
    - 更新Redis BitSet状态
    - 保存分片信息到数据库
    """
    try:
        # 读取分片数据
        chunk_data = await file.read()
        
        # 调用服务层处理分片上传
        uploaded_chunks, progress = await file_service.upload_chunk(
            db=db,
            user=current_user,
            file_md5=fileMd5,
            chunk_index=chunkIndex,
            chunk_data=chunk_data,
            file_name=fileName,
            total_size=totalSize,
            total_chunks=totalChunks,
            org_tag=orgTag,
            is_public=isPublic
        )
        
        return ChunkUploadResponse(
            code=200,
            message="分片上传成功",
            data=ChunkUploadData(
                uploaded=uploaded_chunks,
                progress=progress
            ).dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分片上传失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分片上传失败: {str(e)}"
        )


@upload_router.get("/status", response_model=UploadStatusResponse)
async def get_upload_status(
    file_md5: str = Query(..., description="文件MD5值"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询上传状态接口
    
    - 查询已上传的分片列表
    - 计算上传进度
    """
    try:
        uploaded_chunks, progress, total_chunks = await file_service.get_upload_status(
            db=db,
            user=current_user,
            file_md5=file_md5
        )
        
        return UploadStatusResponse(
            code=200,
            message="Success",
            data=UploadStatusData(
                uploaded=uploaded_chunks,
                progress=progress,
                total_chunks=total_chunks
            ).dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询上传状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询上传状态失败: {str(e)}"
        )


@upload_router.post("/merge", response_model=MergeFileResponse)
async def merge_file(
    request: MergeFileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    文件合并接口
    
    - 验证所有分片已上传
    - 调用MinIO compose API合并分片
    - 清理临时分片
    - 更新文件状态
    - 发送解析任务到Kafka
    """
    try:
        object_url, file_size = await file_service.merge_file(
            db=db,
            user=current_user,
            file_md5=request.file_md5,
            file_name=request.file_name
        )
        
        return MergeFileResponse(
            code=200,
            message="File merged successfully",
            data=MergeFileData(
                object_url=object_url,
                file_size=file_size
            ).dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件合并失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件合并失败: {str(e)}"
        )


# 文档管理相关路由
documents_router = APIRouter()

@documents_router.delete("/{file_md5}", response_model=DeleteFileResponse)
async def delete_file(
    file_md5: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    文件删除接口
    
    - 验证权限
    - 删除Elasticsearch中的向量
    - 删除MinIO中的文件
    - 删除数据库记录
    - 清理Redis缓存
    """
    try:
        await file_service.delete_file(
            db=db,
            user=current_user,
            file_md5=file_md5
        )
        
        return DeleteFileResponse(
            code=200,
            message="文档删除成功",
            data=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )


@documents_router.get("/accessible", response_model=FileListResponse)
async def get_accessible_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户可访问的全部文件列表
    
    - 包括用户上传的文件
    - 包括公开文件
    - 包括用户所属组织的文件
    """
    try:
        files = await file_service.get_accessible_files(
            db=db,
            user=current_user
        )
        
        file_list = [
            FileInfo(
                fileMd5=file.file_md5,
                fileName=file.file_name,
                totalSize=file.total_size,
                status=file.status,
                userId=str(file.user_id),
                orgTag=file.org_tag,
                isPublic=file.is_public,
                createdAt=file.created_at,
                mergedAt=file.merged_at
            )
            for file in files
        ]
        
        return FileListResponse(
            code=200,
            message="获取文件列表成功",
            data=file_list
        )
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件列表失败: {str(e)}"
        )


@documents_router.get("/uploads", response_model=FileUploadListResponse)
async def get_user_uploaded_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户上传的全部文件列表
    """
    try:
        files = await file_service.get_user_uploaded_files(
            db=db,
            user=current_user
        )
        
        file_list = [
            FileUploadInfo(
                fileMd5=file.file_md5,
                fileName=file.file_name,
                totalSize=file.total_size,
                status=file.status,
                userId=str(file.user_id),
                orgTagName=file.org_tag,
                isPublic=file.is_public,
                createdAt=file.created_at,
                mergedAt=file.merged_at
            )
            for file in files
        ]
        
        return FileUploadListResponse(
            code=200,
            message="获取文件列表成功",
            data=file_list
        )
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件列表失败: {str(e)}"
        )

