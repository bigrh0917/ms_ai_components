"""
MinIO 对象存储客户端
"""
from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
from io import BytesIO
from datetime import timedelta
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MinioClient:
    """MinIO 对象存储客户端"""
    
    def __init__(self):
        self.client: Optional[Minio] = None
    
    def connect(self):
        """创建 MinIO 客户端连接"""
        try:
            self.client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            logger.info(f"MinIO 客户端初始化成功: {settings.MINIO_ENDPOINT}")
        except Exception as e:
            logger.error(f"MinIO 客户端初始化失败: {e}")
            raise
    
    def close(self):
        """关闭 MinIO 客户端（MinIO 客户端无需显式关闭）"""
        self.client = None
        logger.info("MinIO 客户端已关闭")
    
    def ensure_bucket(self, bucket_name: str) -> bool:
        """
        确保存储桶存在，如果不存在则创建
        
        Args:
            bucket_name: 存储桶名称
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"创建存储桶成功: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"存储桶操作失败: {e}")
            return False
    
    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: BinaryIO,
        file_size: int,
        content_type: str = "application/octet-stream"
    ) -> bool:
        """
        上传文件到 MinIO
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（文件路径）
            file_data: 文件数据流
            file_size: 文件大小（字节）
            content_type: 文件类型
            
        Returns:
            bool: 上传是否成功
        """
        try:
            # 确保存储桶存在
            self.ensure_bucket(bucket_name)
            
            # 上传文件
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type
            )
            logger.info(f"文件上传成功: {bucket_name}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"文件上传失败: {e}")
            return False
    
    def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> bool:
        """
        上传字节数据到 MinIO
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（文件路径）
            data: 字节数据
            content_type: 文件类型
            
        Returns:
            bool: 上传是否成功
        """
        try:
            file_data = BytesIO(data)
            return self.upload_file(
                bucket_name=bucket_name,
                object_name=object_name,
                file_data=file_data,
                file_size=len(data),
                content_type=content_type
            )
        except Exception as e:
            logger.error(f"字节数据上传失败: {e}")
            return False
    
    def download_file(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """
        从 MinIO 下载文件
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（文件路径）
            
        Returns:
            Optional[bytes]: 文件数据，失败返回 None
        """
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"文件下载成功: {bucket_name}/{object_name}")
            return data
        except S3Error as e:
            logger.error(f"文件下载失败: {e}")
            return None
    
    def delete_file(self, bucket_name: str, object_name: str) -> bool:
        """
        删除 MinIO 中的文件
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（文件路径）
            
        Returns:
            bool: 删除是否成功
        """
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"文件删除成功: {bucket_name}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"文件删除失败: {e}")
            return False
    
    def file_exists(self, bucket_name: str, object_name: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（文件路径）
            
        Returns:
            bool: 文件是否存在
        """
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error:
            return False
    
    def get_file_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> Optional[str]:
        """
        获取文件的预签名 URL（临时访问链接）
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（文件路径）
            expires: 过期时间，默认 1 小时
            
        Returns:
            Optional[str]: 预签名 URL，失败返回 None
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"获取预签名 URL 失败: {e}")
            return None
    
    def list_files(self, bucket_name: str, prefix: str = "") -> list:
        """
        列出存储桶中的文件
        
        Args:
            bucket_name: 存储桶名称
            prefix: 对象名称前缀（用于过滤）
            
        Returns:
            list: 文件对象列表
        """
        try:
            objects = self.client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            file_list = []
            for obj in objects:
                file_list.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag
                })
            
            return file_list
        except S3Error as e:
            logger.error(f"列出文件失败: {e}")
            return []
    
    def get_file_info(self, bucket_name: str, object_name: str) -> Optional[dict]:
        """
        获取文件信息
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（文件路径）
            
        Returns:
            Optional[dict]: 文件信息，失败返回 None
        """
        try:
            stat = self.client.stat_object(bucket_name, object_name)
            return {
                "name": stat.object_name,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "etag": stat.etag,
                "metadata": stat.metadata
            }
        except S3Error as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 尝试列出存储桶来检查连接
            list(self.client.list_buckets())
            return True
        except Exception as e:
            logger.error(f"MinIO 健康检查失败: {e}")
            return False
    
    def get_status(self) -> dict:
        """获取 MinIO 客户端状态"""
        if not self.client:
            return {"error": "MinIO 客户端未初始化"}
        
        try:
            buckets = list(self.client.list_buckets())
            return {
                "状态": "已连接",
                "端点": settings.MINIO_ENDPOINT,
                "安全连接": settings.MINIO_SECURE,
                "存储桶数量": len(buckets),
                "存储桶列表": [bucket.name for bucket in buckets]
            }
        except Exception as e:
            return {
                "状态": "连接失败",
                "错误": str(e)
            }


# 全局 MinIO 客户端实例
minio_client = MinioClient()

