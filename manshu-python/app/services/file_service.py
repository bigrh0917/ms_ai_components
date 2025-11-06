"""
文件服务层
"""
import hashlib
import json
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.file import FileUpload, ChunkInfo, DocumentVector
from app.models.user import User, UserRole
from app.clients.minio_client import minio_client
from app.clients.redis_client import redis_client
from app.clients.kafka_client import kafka_client
from app.clients.elasticsearch_client import es_client
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileService:
    """文件服务"""

    @staticmethod
    def calculate_md5(data: bytes) -> str:
        """计算数据的MD5值"""
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def get_redis_chunk_key(file_md5: str) -> str:
        """获取Redis中分片位图的键"""
        return f"upload:chunks:{file_md5}"

    @staticmethod
    def get_redis_meta_key(file_md5: str) -> str:
        """获取Redis中上传任务元数据的键"""
        return f"upload:meta:{file_md5}"

    async def upload_chunk(
        self,
        db: AsyncSession,
        user: User,
        file_md5: str,
        chunk_index: int,
        chunk_data: bytes,
        file_name: str,
        total_size: int,
        total_chunks: Optional[int] = None,
        org_tag: Optional[str] = None,
        is_public: bool = False
    ) -> Tuple[List[int], float]:
        """
        上传文件分片
        
        Returns:
            Tuple[List[int], float]: (已上传分片索引列表, 上传进度百分比)
        """
        # 1. 验证分片数据完整性（计算分片MD5）
        chunk_md5 = self.calculate_md5(chunk_data)
        
        # 2. 检查分片是否已上传（幂等性）
        redis_key = self.get_redis_chunk_key(file_md5)
        is_uploaded = await redis_client.get_bit(redis_key, chunk_index)
        
        # 3. 检查数据库中的分片记录
        existing_chunk_result = await db.execute(
            select(ChunkInfo).where(
                and_(
                    ChunkInfo.file_md5 == file_md5,
                    ChunkInfo.chunk_index == chunk_index
                )
            )
        )
        existing_chunk = existing_chunk_result.scalar_one_or_none()
        
        if is_uploaded == 1 and existing_chunk:
            # Redis和数据库都已存在，但需要验证MinIO中是否真的存在
            chunk_path = existing_chunk.storage_path
            if minio_client.file_exists(settings.MINIO_DEFAULT_BUCKET, chunk_path):
                # MinIO中也存在，可以跳过上传
                logger.info(f"分片 {chunk_index} 已存在（Redis+DB+MinIO），跳过上传: {file_md5}")
            else:
                # MinIO中不存在，需要重新上传
                logger.warning(f"分片 {chunk_index} 在Redis和DB中存在，但MinIO中不存在，重新上传: {file_md5}")
                chunk_path = minio_client.build_temp_chunk_path(file_md5, chunk_index)
                success = minio_client.upload_bytes(
                    bucket_name=settings.MINIO_DEFAULT_BUCKET,
                    object_name=chunk_path,
                    data=chunk_data
                )
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"分片重新上传失败: {file_md5}/{chunk_index}"
                    )
                # 更新存储路径（如果路径不同）
                if existing_chunk.storage_path != chunk_path:
                    existing_chunk.storage_path = chunk_path
                    await db.commit()
                logger.info(f"分片 {chunk_index} 重新上传成功: {file_md5}")
        else:
            # 需要上传：要么Redis中没有，要么数据库中没有
            if is_uploaded == 1 and not existing_chunk:
                # Redis中有但数据库中没有，需要修复数据一致性
                logger.warning(f"分片 {chunk_index} 在Redis中但不在数据库中，尝试修复: {file_md5}")
                # 尝试从MinIO获取路径（如果MinIO中存在）
                chunk_path = minio_client.build_temp_chunk_path(file_md5, chunk_index)
                # 检查MinIO中是否存在
                if not minio_client.file_exists(settings.MINIO_DEFAULT_BUCKET, chunk_path):
                    # MinIO中也不存在，需要重新上传
                    logger.warning(f"分片 {chunk_index} 在MinIO中也不存在，需要重新上传: {file_md5}")
                    chunk_path = minio_client.build_temp_chunk_path(file_md5, chunk_index)
                    success = minio_client.upload_bytes(
                        bucket_name=settings.MINIO_DEFAULT_BUCKET,
                        object_name=chunk_path,
                        data=chunk_data
                    )
                    if not success:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"分片上传失败: {file_md5}/{chunk_index}"
                        )
                    # 更新Redis
                    await redis_client.set_bit(redis_key, chunk_index, 1)
            else:
                # 正常上传流程
                chunk_path = minio_client.build_temp_chunk_path(file_md5, chunk_index)
                success = minio_client.upload_bytes(
                    bucket_name=settings.MINIO_DEFAULT_BUCKET,
                    object_name=chunk_path,
                    data=chunk_data
                )
                
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"分片上传失败: {file_md5}/{chunk_index}"
                    )
                
                # 验证MinIO中是否真的存在（防止上传返回成功但实际失败的情况）
                if not minio_client.file_exists(settings.MINIO_DEFAULT_BUCKET, chunk_path):
                    logger.error(f"分片 {chunk_index} 上传返回成功，但MinIO中不存在，尝试重新上传: {file_md5}")
                    # 尝试重新上传
                    retry_success = minio_client.upload_bytes(
                        bucket_name=settings.MINIO_DEFAULT_BUCKET,
                        object_name=chunk_path,
                        data=chunk_data
                    )
                    if not retry_success or not minio_client.file_exists(settings.MINIO_DEFAULT_BUCKET, chunk_path):
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"分片上传验证失败: {file_md5}/{chunk_index}"
                        )
                    logger.info(f"分片 {chunk_index} 重新上传成功: {file_md5}")
                
                # 更新Redis BitSet（标记分片已上传）
                try:
                    await redis_client.set_bit(redis_key, chunk_index, 1)
                except Exception as e:
                    logger.warning(f"Redis更新失败: {e}，将在查询时修复")
            
            # 5. 保存分片信息到数据库（如果不存在）
            if not existing_chunk:
                chunk_info = ChunkInfo(
                    file_md5=file_md5,
                    chunk_index=chunk_index,
                    chunk_md5=chunk_md5,
                    storage_path=chunk_path
                )
                db.add(chunk_info)
        
        # 6. 创建或更新文件上传记录
        file_upload_result = await db.execute(
            select(FileUpload).where(
                and_(
                    FileUpload.file_md5 == file_md5,
                    FileUpload.user_id == user.id
                )
            )
        )
        file_record = file_upload_result.scalar_one_or_none()
        
        if not file_record:
            # 使用用户的主组织标签作为默认值
            default_org_tag = org_tag or user.primary_org
            
            file_record = FileUpload(
                file_md5=file_md5,
                file_name=file_name,
                total_size=total_size,
                status=0,  # 上传中
                user_id=user.id,
                org_tag=default_org_tag,
                is_public=is_public
            )
            db.add(file_record)
            
            # 保存元数据到Redis
            meta_key = self.get_redis_meta_key(file_md5)
            meta_data = {
                "file_md5": file_md5,
                "file_name": file_name,
                "total_size": total_size,
                "total_chunks": total_chunks,
                "user_id": user.id
            }
            try:
                await redis_client.set(meta_key, json.dumps(meta_data), expire=3600 * 24)  # 24小时过期
            except Exception as e:
                logger.warning(f"Redis元数据保存失败: {e}")
        else:
            # 更新文件记录
            if org_tag:
                file_record.org_tag = org_tag
            if is_public is not None:
                file_record.is_public = is_public
        
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"数据库提交失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"数据库写入失败: {str(e)}"
            )
        
        # 7. 获取已上传分片列表和进度
        uploaded_chunks = await self.get_uploaded_chunks(file_md5, total_chunks or 0)
        progress = await redis_client.get_bitmap_progress(redis_key, total_chunks or 0)
        
        return uploaded_chunks, progress * 100

    async def get_uploaded_chunks(self, file_md5: str, total_chunks: int) -> List[int]:
        """获取已上传的分片索引列表"""
        if total_chunks <= 0:
            return []
        
        redis_key = self.get_redis_chunk_key(file_md5)
        uploaded = []
        
        for i in range(total_chunks):
            if await redis_client.get_bit(redis_key, i) == 1:
                uploaded.append(i)
        
        return uploaded

    async def get_upload_status(
        self,
        db: AsyncSession,
        user: User,
        file_md5: str
    ) -> Tuple[List[int], float, int]:
        """
        获取上传状态
        
        Returns:
            Tuple[List[int], float, int]: (已上传分片列表, 进度百分比, 总分片数)
        """
        # 查询文件记录
        file_upload_result = await db.execute(
            select(FileUpload).where(
                and_(
                    FileUpload.file_md5 == file_md5,
                    FileUpload.user_id == user.id
                )
            )
        )
        file_record = file_upload_result.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload record not found"
            )
        
        # 查询分片总数（从数据库查询）
        chunks_result = await db.execute(
            select(ChunkInfo).where(ChunkInfo.file_md5 == file_md5)
        )
        chunks = chunks_result.scalars().all()
        total_chunks = len(chunks) if chunks else 0
        
        # 如果Redis中没有状态，从MySQL重建
        redis_key = self.get_redis_chunk_key(file_md5)
        if not await redis_client.exists(redis_key) and chunks:
            logger.info(f"Redis状态丢失，从MySQL重建: {file_md5}")
            for chunk in chunks:
                await redis_client.set_bit(redis_key, chunk.chunk_index, 1)
        
        # 从Redis获取已上传分片
        uploaded_chunks = await self.get_uploaded_chunks(file_md5, total_chunks)
        progress = await redis_client.get_bitmap_progress(redis_key, total_chunks)
        
        return uploaded_chunks, progress * 100, total_chunks

    async def merge_file(
        self,
        db: AsyncSession,
        user: User,
        file_md5: str,
        file_name: str
    ) -> Tuple[str, int]:
        """
        合并文件分片
        
        Returns:
            Tuple[str, int]: (文件访问URL, 文件大小)
        """
        # 1. 验证文件记录
        file_upload_result = await db.execute(
            select(FileUpload).where(
                and_(
                    FileUpload.file_md5 == file_md5,
                    FileUpload.user_id == user.id
                )
            )
        )
        file_record = file_upload_result.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # 2. 查询所有分片
        chunks_result = await db.execute(
            select(ChunkInfo)
            .where(ChunkInfo.file_md5 == file_md5)
            .order_by(ChunkInfo.chunk_index)
        )
        chunks = chunks_result.scalars().all()
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chunks found"
            )
        
        total_chunks = len(chunks)
        
        # 3. 验证所有分片是否已上传
        redis_key = self.get_redis_chunk_key(file_md5)
        for i in range(total_chunks):
            if await redis_client.get_bit(redis_key, i) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not all chunks have been uploaded"
                )
        
        # 4. 合并分片（使用MinIO的compose功能）
        dest_path = minio_client.build_document_path(user.id, file_name)
        success = minio_client.merge_chunks(
            bucket_name=settings.MINIO_DEFAULT_BUCKET,
            file_md5=file_md5,
            total_chunks=total_chunks,
            dest_object=dest_path
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File merge failed"
            )
        
        # 5. 清理临时分片
        temp_prefix = f"temp/{file_md5}/"
        minio_client.delete_prefix(
            bucket_name=settings.MINIO_DEFAULT_BUCKET,
            prefix=temp_prefix
        )
        
        # 6. 更新文件状态
        file_record.status = 1  # 已完成
        await db.commit()
        
        # 7. 清理Redis中的分片位图
        await redis_client.clear_bitmap(redis_key)
        
        # 8. 发送解析任务到Kafka
        kafka_message = {
            "file_md5": file_md5,
            "file_name": file_name,
            "storage_path": dest_path,
            "user_id": user.id,
            "org_tag": file_record.org_tag,
            "is_public": file_record.is_public
        }
        try:
            success = await kafka_client.send_message(
                topic="document_parse",
                value=kafka_message,
                key=file_md5
            )
            if not success:
                logger.warning(f"Kafka消息发送失败（生产者可能未初始化），但文件合并成功")
        except Exception as e:
            logger.warning(f"Kafka消息发送失败: {e}，但文件合并成功")
        
        # 9. 生成文件访问URL
        file_url = minio_client.get_file_url(
            bucket_name=settings.MINIO_DEFAULT_BUCKET,
            object_name=dest_path
        ) or f"{settings.MINIO_ENDPOINT}/{settings.MINIO_DEFAULT_BUCKET}/{dest_path}"
        
        return file_url, file_record.total_size

    async def delete_file(
        self,
        db: AsyncSession,
        user: User,
        file_md5: str
    ) -> bool:
        """
        删除文件（包括MinIO文件、数据库记录、Elasticsearch向量）
        管理员可以删除任何文件
        
        Returns:
            bool: 是否删除成功
        """
        # 1. 查询文件记录
        # 如果是管理员，不需要限制 user_id
        if user.role == UserRole.ADMIN:
            file_upload_result = await db.execute(
                select(FileUpload).where(FileUpload.file_md5 == file_md5)
            )
        else:
            file_upload_result = await db.execute(
                select(FileUpload).where(
                    and_(
                        FileUpload.file_md5 == file_md5,
                        FileUpload.user_id == user.id
                    )
                )
            )
        file_record = file_upload_result.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        # 2. 权限检查（文件所有者或管理员可以删除）
        if file_record.user_id != user.id and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此文档"
            )
        
        try:
            # 3. 从Elasticsearch删除文档向量
            # 查询所有相关的向量记录
            vectors_result = await db.execute(
                select(DocumentVector).where(DocumentVector.file_md5 == file_md5)
            )
            vectors = vectors_result.scalars().all()
            
            for vector in vectors:
                # 构建Elasticsearch文档ID：file_md5_chunk_id
                doc_id = f"{file_md5}_{vector.chunk_id}"
                try:
                    await es_client.delete_document(
                        index=settings.ES_DEFAULT_INDEX,
                        doc_id=doc_id
                    )
                except Exception as e:
                    logger.warning(f"Elasticsearch删除失败: {e}")
            
            # 4. 删除MinIO中的文件
            if file_record.status == 1:  # 已合并的文件
                # 使用文件所有者的 user_id 构建路径
                file_path = minio_client.build_document_path(file_record.user_id, file_record.file_name)
                minio_client.delete_file(
                    bucket_name=settings.MINIO_DEFAULT_BUCKET,
                    object_name=file_path
                )
            else:  # 上传中的文件，删除临时分片
                temp_prefix = f"temp/{file_md5}/"
                minio_client.delete_prefix(
                    bucket_name=settings.MINIO_DEFAULT_BUCKET,
                    prefix=temp_prefix
                )
            
            # 5. 删除数据库记录（级联删除会自动删除chunks和vectors）
            await db.delete(file_record)
            await db.commit()
            
            # 6. 清理Redis缓存
            await redis_client.clear_bitmap(self.get_redis_chunk_key(file_md5))
            await redis_client.delete(self.get_redis_meta_key(file_md5))
            
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"删除文档失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文档失败: {str(e)}"
            )

    async def get_accessible_files(
        self,
        db: AsyncSession,
        user: User
    ) -> List[FileUpload]:
        """
        获取用户可访问的所有文件（包括用户上传的、公开的、所属组织的）
        管理员可以查看所有文件
        """
        # 如果是管理员，返回所有文件
        if user.role == UserRole.ADMIN:
            result = await db.execute(
                select(FileUpload)
                .order_by(FileUpload.created_at.desc())
            )
            return result.scalars().all()
        
        # 普通用户的逻辑
        # 构建查询条件
        conditions = []
        
        # 1. 用户自己上传的文件
        conditions.append(FileUpload.user_id == user.id)
        
        # 2. 公开的文件
        conditions.append(FileUpload.is_public == True)
        
        # 3. 用户所属组织的文件
        if user.org_tags:
            org_tags_list = [tag.strip() for tag in user.org_tags.split(",") if tag.strip()]
            if org_tags_list:
                conditions.append(FileUpload.org_tag.in_(org_tags_list))
        
        # 执行查询
        result = await db.execute(
            select(FileUpload)
            .where(or_(*conditions))
            .order_by(FileUpload.created_at.desc())
        )
        
        return result.scalars().all()

    async def get_user_uploaded_files(
        self,
        db: AsyncSession,
        user: User
    ) -> List[FileUpload]:
        """获取用户上传的所有文件"""
        result = await db.execute(
            select(FileUpload)
            .where(FileUpload.user_id == user.id)
            .order_by(FileUpload.created_at.desc())
        )
        
        return result.scalars().all()


# 全局服务实例
file_service = FileService()

