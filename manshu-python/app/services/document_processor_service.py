"""
文档处理服务 - 处理Kafka消息，执行文件解析、向量化和索引
"""
import re
import asyncio
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from tika import parser as tika_parser
from app.clients.minio_client import minio_client
from app.clients.elasticsearch_client import es_client
from app.clients.db_client import db_client
from app.services.embedding_service import embedding_service
from app.services.search_service import search_service
from app.models.file import FileUpload, DocumentVector
from app.models.user import User
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentProcessorService:
    """文档处理服务 - 处理Kafka消息，执行异步向量化"""
    
    def __init__(self):
        self.chunk_size = 500  # 文本块大小
        self.chunk_overlap = 50  # 文本块重叠大小
    
    def parse_text_content(self, file_data: bytes, file_name: str) -> str:
        """
        解析文件内容，提取纯文本（使用 Apache Tika）
        
        支持的文件格式：
        - 文档：PDF, Word (.doc, .docx), Excel (.xls, .xlsx), PowerPoint (.ppt, .pptx)
        - 文本：TXT, Markdown, HTML, XML, JSON, CSV
        - 其他：RTF, ODT, ODS, ODP 等
        
        Args:
            file_data: 文件字节数据
            file_name: 文件名（用于判断文件类型）
            
        Returns:
            提取的纯文本内容
        """
        try:
            # 首先尝试使用 Tika 解析文件（支持多种格式）
            try:
                parsed = tika_parser.from_buffer(file_data)
                
                if parsed and 'content' in parsed and parsed['content']:
                    text_content = parsed['content']
                    
                    # 记录检测到的文件类型（如果 Tika 提供了元数据）
                    if 'metadata' in parsed and parsed['metadata']:
                        content_type = parsed['metadata'].get('Content-Type', 'unknown')
                        logger.debug(f"Tika 检测到的文件类型: {content_type}")
                    
                    logger.info(f"使用 Tika 解析文件: {file_name}")
                else:
                    # Tika 未能提取内容，使用降级方案
                    logger.warning(f"Tika 未能提取内容，使用降级方案: {file_name}")
                    text_content = None
                    
            except Exception as tika_error:
                # Tika 解析失败，使用降级方案
                logger.warning(f"Tika 解析失败: {tika_error}，使用降级方案: {file_name}")
                text_content = None
            
            # 降级处理：如果 Tika 失败，尝试 UTF-8 解码（适用于纯文本和 Markdown）
            if not text_content:
                try:
                    text_content = file_data.decode('utf-8')
                    logger.info(f"使用 UTF-8 解码作为降级方案: {file_name}")
                except UnicodeDecodeError:
                    raise ValueError(f"无法解析文件内容（Tika 失败且非 UTF-8 编码）: {file_name}")
            
            if not text_content or not text_content.strip():
                raise ValueError(f"文件内容为空: {file_name}")
            
            # 清理文本内容
            text_content = text_content.strip()
            
            # 如果是 Markdown 文件，移除 Markdown 标记（可选，保持原有行为）
            if file_name.lower().endswith(('.md', '.markdown')):
                text_content = self._clean_markdown(text_content)
            
            # 清理多余的空行和空白字符
            text_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', text_content)
            text_content = text_content.strip()
            
            logger.info(f"文件解析完成: {file_name}, 文本长度: {len(text_content)} 字符")
            return text_content
            
        except ValueError:
            # 重新抛出 ValueError
            raise
        except Exception as e:
            logger.error(f"文件解析失败: {file_name}, 错误: {e}", exc_info=True)
            raise ValueError(f"文件解析失败: {str(e)}")
    
    def _clean_markdown(self, text: str) -> str:
        """
        清理 Markdown 标记，保留纯文本
        
        Args:
            text: Markdown 文本
            
        Returns:
            清理后的纯文本
        """
        # 移除标题标记
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        # 移除列表标记
        text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
        # 移除代码块标记
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]+`', '', text)
        # 移除链接标记 [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # 移除粗体/斜体标记
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        return text
    
    def split_text_into_chunks(self, text: str) -> List[Dict[str, Any]]:
        """
        将文本分割成块
        
        Args:
            text: 文本内容
            
        Returns:
            文本块列表，每个块包含 chunk_id 和 text
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        chunk_id = 0
        max_iterations = len(text) // max(1, self.chunk_size - self.chunk_overlap) + 10
        
        iteration = 0
        while start < len(text) and iteration < max_iterations:
            iteration += 1
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text
                })
                chunk_id += 1
            
            # 确保向前推进
            next_start = end - self.chunk_overlap
            if next_start <= start:
                next_start = start + max(1, self.chunk_size - self.chunk_overlap)
            
            start = next_start
        
        if iteration >= max_iterations:
            logger.warning(f"文本分块达到最大迭代次数 ({max_iterations})")
        
        logger.info(f"文本分块完成: 共 {len(chunks)} 个文本块")
        return chunks
    
    async def process_document(
        self,
        file_md5: str,
        file_name: str,
        storage_path: str,
        user_id: int,
        org_tag: Optional[str] = None,
        is_public: bool = False
    ) -> bool:
        """
        处理文档：下载、解析、向量化、索引
        
        Args:
            file_md5: 文件MD5
            file_name: 文件名
            storage_path: MinIO存储路径
            user_id: 用户ID
            org_tag: 组织标签
            is_public: 是否公开
            
        Returns:
            是否处理成功
        """
        db = None
        try:
            # 获取数据库会话
            async for session in db_client.get_session():
                db = session
                break
            
            if not db:
                logger.error("无法获取数据库会话")
                return False
            
            logger.info(f"开始处理文档: file_md5={file_md5}, file_name={file_name}")
            
            # 1. 从MinIO下载文件
            logger.info(f"从MinIO下载文件: {storage_path}")
            file_data = minio_client.download_file(
                bucket_name=settings.MINIO_DEFAULT_BUCKET,
                object_name=storage_path
            )
            
            if not file_data:
                logger.error(f"文件下载失败: {storage_path}")
                return False
            
            logger.info(f"文件下载成功，大小: {len(file_data)} 字节")
            
            # 2. 解析文件内容
            text_content = self.parse_text_content(file_data, file_name)
            
            if not text_content:
                logger.warning(f"文件内容为空: {file_name}")
                return False
            
            # 3. 文本分块
            chunks = self.split_text_into_chunks(text_content)
            
            if not chunks:
                logger.warning(f"文本分块为空: {file_name}")
                return False
            
            # 4. 确保Elasticsearch索引存在
            await search_service.ensure_index_exists()
            
            # 5. 批量向量化
            texts = [chunk["text"] for chunk in chunks]
            logger.info(f"开始向量化: {len(texts)} 个文本块")
            
            vectors = await embedding_service.embed_batch(texts)
            successful_vectors = sum(1 for v in vectors if v is not None)
            logger.info(f"向量化完成: {successful_vectors}/{len(chunks)}")
            
            if successful_vectors == 0:
                logger.error("所有文本块向量化失败")
                return False
            
            # 6. 获取文件记录和用户信息
            file_result = await db.execute(
                select(FileUpload).where(
                    FileUpload.file_md5 == file_md5,
                    FileUpload.user_id == user_id
                )
            )
            file_record = file_result.scalar_one_or_none()
            
            if not file_record:
                logger.error(f"文件记录不存在: file_md5={file_md5}, user_id={user_id}")
                return False
            
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"用户不存在: user_id={user_id}")
                return False
            
            # 7. 保存向量到数据库并索引到Elasticsearch
            success_count = 0
            org_tag = org_tag or file_record.org_tag or "DEFAULT"
            is_public = is_public if is_public is not None else (file_record.is_public if file_record.is_public is not None else False)
            
            for chunk, vector in zip(chunks, vectors):
                if vector is None:
                    logger.warning(f"跳过块 {chunk['chunk_id']}（向量化失败）")
                    continue
                
                # 保存到数据库
                doc_vector = DocumentVector(
                    file_md5=file_md5,
                    chunk_id=chunk["chunk_id"],
                    text_content=chunk["text"],
                    model_version=settings.OPENAI_EMBEDDING_MODEL
                )
                db.add(doc_vector)
                
                # 索引到Elasticsearch
                es_doc = {
                    "file_md5": file_md5,
                    "chunk_id": chunk["chunk_id"],
                    "text_content": chunk["text"],
                    "vector": vector,
                    "user_id": user_id,
                    "org_tag": org_tag,
                    "is_public": is_public,
                    "file_name": file_name,
                    "model_version": settings.OPENAI_EMBEDDING_MODEL
                }
                
                doc_id = f"{file_md5}_{chunk['chunk_id']}"
                result = await es_client.index_document(
                    index=search_service.INDEX_NAME,
                    document=es_doc,
                    doc_id=doc_id
                )
                
                if result:
                    success_count += 1
                    logger.debug(f"索引成功: {doc_id}")
            
            # 提交数据库事务
            await db.commit()
            
            # 刷新Elasticsearch索引
            await es_client.refresh_index(search_service.INDEX_NAME)
            
            logger.info(f"文档处理完成: file_md5={file_md5}, 成功索引 {success_count}/{len(chunks)} 个文本块")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"处理文档失败: file_md5={file_md5}, 错误: {e}", exc_info=True)
            if db:
                try:
                    await db.rollback()
                except:
                    pass
            return False
    
    async def handle_kafka_message(self, message) -> bool:
        """
        处理Kafka消息
        
        Args:
            message: Kafka消息对象
            
        Returns:
            是否处理成功
        """
        try:
            # 解析消息
            message_data = message.value
            
            if not isinstance(message_data, dict):
                logger.error(f"无效的消息格式: {type(message_data)}, 消息内容: {message_data}")
                return False
            
            file_md5 = message_data.get("file_md5")
            file_name = message_data.get("file_name")
            storage_path = message_data.get("storage_path")
            user_id = message_data.get("user_id")
            org_tag = message_data.get("org_tag")
            is_public = message_data.get("is_public", False)
            
            # 验证必要字段
            missing_fields = []
            if not file_md5:
                missing_fields.append("file_md5")
            if not file_name:
                missing_fields.append("file_name")
            if not storage_path:
                missing_fields.append("storage_path")
            if not user_id:
                missing_fields.append("user_id")
            
            if missing_fields:
                logger.error(f"消息缺少必要字段: {missing_fields}, 消息内容: {message_data}")
                return False
            
            logger.info(
                f"收到文档处理消息: file_md5={file_md5}, file_name={file_name}, "
                f"user_id={user_id}, topic={message.topic}, partition={message.partition}, offset={message.offset}"
            )
            
            # 处理文档（带重试机制）
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    success = await self.process_document(
                        file_md5=file_md5,
                        file_name=file_name,
                        storage_path=storage_path,
                        user_id=user_id,
                        org_tag=org_tag,
                        is_public=is_public
                    )
                    
                    if success:
                        logger.info(f"文档处理成功: file_md5={file_md5}, 重试次数: {retry_count}")
                        break
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(f"文档处理失败，准备重试 ({retry_count}/{max_retries}): file_md5={file_md5}")
                            await asyncio.sleep(2 ** retry_count)  # 指数退避
                        else:
                            logger.error(f"文档处理失败，已达到最大重试次数: file_md5={file_md5}")
                            
                except Exception as e:
                    retry_count += 1
                    logger.error(f"文档处理异常 (重试 {retry_count}/{max_retries}): file_md5={file_md5}, 错误: {e}", exc_info=True)
                    if retry_count < max_retries:
                        await asyncio.sleep(2 ** retry_count)  # 指数退避
                    else:
                        logger.error(f"文档处理异常，已达到最大重试次数: file_md5={file_md5}")
            
            return success
            
        except Exception as e:
            logger.error(f"处理Kafka消息失败: {e}", exc_info=True)
            return False


# 全局服务实例
document_processor_service = DocumentProcessorService()

