"""
检索服务 - 混合检索核心逻辑
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.file import FileUpload, DocumentVector
from app.models.user import User
from app.clients.elasticsearch_client import es_client
from app.services.embedding_service import embedding_service
from app.services.permission_service import permission_service
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SearchService:
    """检索服务"""
    
    # Elasticsearch索引名称
    INDEX_NAME = settings.ES_DEFAULT_INDEX
    
    # 向量维度
    VECTOR_DIMENSIONS = settings.OPENAI_EMBEDDING_DIMENSIONS
    
    @staticmethod
    def get_index_mappings() -> Dict[str, Any]:
        """
        获取Elasticsearch索引的mapping配置
        
        Returns:
            索引mapping配置
        """
        return {
            "properties": {
                "file_md5": {
                    "type": "keyword"
                },
                "chunk_id": {
                    "type": "integer"
                },
                "text_content": {
                    "type": "text",
                    "analyzer": "ik_max_word",  # 使用IK分词器（最大词粒度）
                    "search_analyzer": "ik_smart",  # 搜索时使用智能分词
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "vector": {
                    "type": "dense_vector",
                    "dims": SearchService.VECTOR_DIMENSIONS,  # 1536维
                    "index": True,  # 启用索引以加速检索
                    "similarity": "cosine"  # 余弦相似度
                },
                "user_id": {
                    "type": "long"
                },
                "org_tag": {
                    "type": "keyword"
                },
                "is_public": {
                    "type": "boolean"
                },
                "file_name": {
                    "type": "keyword"
                },
                "model_version": {
                    "type": "keyword"
                }
            }
        }
    
    @staticmethod
    def get_index_settings() -> Dict[str, Any]:
        """
        获取Elasticsearch索引的settings配置
        
        Returns:
            索引settings配置
        """
        return {
            "number_of_shards": 1,  # 分片数（可根据数据量调整）
            "number_of_replicas": 0,  # 副本数（开发环境可设为0）
            "analysis": {
                "analyzer": {
                    "ik_max_word": {
                        "type": "ik_max_word"
                    },
                    "ik_smart": {
                        "type": "ik_smart"
                    }
                }
            }
        }
    
    @staticmethod
    async def ensure_index_exists() -> bool:
        """
        确保Elasticsearch索引存在，如果不存在则创建
        
        Returns:
            是否成功
        """
        try:
            # 检查索引是否存在
            exists = await es_client.index_exists(SearchService.INDEX_NAME)
            
            if exists:
                logger.info(f"索引 {SearchService.INDEX_NAME} 已存在")
                return True
            
            # 创建索引
            logger.info(f"创建索引 {SearchService.INDEX_NAME}...")
            try:
                success = await es_client.create_index(
                    index=SearchService.INDEX_NAME,
                    mappings=SearchService.get_index_mappings(),
                    settings=SearchService.get_index_settings()
                )
                
                if success:
                    logger.info(f"索引 {SearchService.INDEX_NAME} 创建成功")
                else:
                    logger.error(f"索引 {SearchService.INDEX_NAME} 创建失败（create_index 返回 False）")
                    logger.error("⚠️ 索引创建失败，后续查询可能无法正常工作")
                    logger.error("请查看上方的详细错误信息（来自 es_client.create_index）")
                    logger.error("常见原因：")
                    logger.error("  1. IK 分词器插件未安装")
                    logger.error("  2. Elasticsearch 连接失败")
                    logger.error("  3. 索引配置错误")
                
                return success
            except Exception as create_error:
                logger.error(f"调用 create_index 时发生异常: {type(create_error).__name__}: {create_error}")
                logger.error(f"异常详情: {repr(create_error)}", exc_info=True)
                logger.error("这可能是由于：")
                logger.error("  1. Elasticsearch 服务未运行或无法连接")
                logger.error("  2. IK 分词器插件未安装（如果使用了 IK 分词器）")
                logger.error("  3. 网络连接问题")
                return False
            
        except Exception as e:
            logger.error(f"确保索引存在时出错: {e}", exc_info=True)
            return False
    
    @staticmethod
    def build_hybrid_query(
        query_vector: List[float],
        query_text: str,
        permission_filters: List[Dict[str, Any]],
        vector_weight: float = 0.7,
        text_weight: float = 0.3
    ) -> Dict[str, Any]:
        """
        构建混合检索查询（向量检索 + 全文检索）
        
        Args:
            query_vector: 查询向量
            query_text: 查询文本
            permission_filters: 权限过滤条件
            vector_weight: 向量检索权重（默认0.7）
            text_weight: 全文检索权重（默认0.3）
            
        Returns:
            Elasticsearch查询DSL
        """
        # 构建should子句（向量检索和全文检索）
        should_clauses = []
        
        # 1. 向量相似度检索（使用script_score）
        if query_vector:
            # 检查向量维度
            if len(query_vector) != SearchService.VECTOR_DIMENSIONS:
                logger.warning(f"查询向量维度({len(query_vector)})与配置维度({SearchService.VECTOR_DIMENSIONS})不匹配")
            
            # 使用更安全的script_score查询（兼容Elasticsearch 8.x）
            should_clauses.append({
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": """
                            // 检查向量字段是否存在且不为空
                            if (doc['vector'].size() == 0) {
                                return 0.0;
                            }
                            
                            int vectorSize = doc['vector'].size();
                            
                            // 检查维度是否匹配
                            if (params.query_vector.length != vectorSize) {
                                return 0.0;
                            }
                            
                            // 计算余弦相似度
                            double dotProduct = 0.0;
                            double normA = 0.0;
                            double normB = 0.0;
                            
                            for (int i = 0; i < params.query_vector.length; i++) {
                                double v1 = params.query_vector[i];
                                double v2 = doc['vector'].get(i);
                                dotProduct += v1 * v2;
                                normA += v1 * v1;
                                normB += v2 * v2;
                            }
                            
                            // 避免除以零
                            double denominator = Math.sqrt(normA) * Math.sqrt(normB);
                            if (denominator == 0.0) {
                                return 0.0;
                            }
                            
                            double similarity = dotProduct / denominator;
                            
                            // 确保返回值在合理范围内（-1到1之间）
                            if (Double.isNaN(similarity) || Double.isInfinite(similarity)) {
                                return 0.0;
                            }
                            
                            return similarity;
                        """,
                        "params": {
                            "query_vector": query_vector
                        }
                    },
                    "boost": vector_weight
                }
            })
        
        # 2. 全文检索（关键词匹配）
        if query_text and query_text.strip():
            should_clauses.append({
                "match": {
                    "text_content": {
                        "query": query_text,
                        "boost": text_weight
                    }
                }
            })
        
        # 构建完整查询
        # 权限过滤条件应该使用 OR 关系（should），而不是 AND 关系（filter）
        # 因为用户只要满足其中一个条件就可以访问（自己的 OR 公开的 OR 默认标签的 OR 有权限的组织标签的）
        # 注意：在 filter 中使用 bool.should 时，需要确保 minimum_should_match 生效
        if permission_filters:
            # 如果有多个权限条件，使用 bool.should 实现 OR 关系
            if len(permission_filters) == 1:
                # 只有一个条件，直接使用
                permission_filter = permission_filters[0]
            else:
                # 多个条件，使用 bool.should
                permission_filter = {
                    "bool": {
                        "should": permission_filters,
                        "minimum_should_match": 1
                    }
                }
        else:
            permission_filter = {"match_all": {}}
        
        query = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "filter": [permission_filter],
                    "minimum_should_match": 1 if should_clauses else 0
                }
            }
        }
        
        return query
    
    @staticmethod
    async def hybrid_search(
        db: AsyncSession,
        user: User,
        query_text: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        执行混合检索
        
        Args:
            db: 数据库会话
            user: 当前用户
            query_text: 查询文本
            top_k: 返回结果数量
            
        Returns:
            检索结果列表，每个结果包含：
            - file_md5: 文件MD5
            - chunk_id: 分块ID
            - text_content: 文本内容
            - score: 相关性分数
            - file_name: 文件名（从数据库查询）
        """
        # 1. 确保索引存在
        index_exists = await SearchService.ensure_index_exists()
        if not index_exists:
            logger.error("⚠️ 索引创建失败，无法执行检索")
            logger.error("请检查 Elasticsearch 连接和 IK 分词器插件是否已安装")
            return []
        
        # 2. 向量化查询文本
        logger.info(f"向量化查询文本: {query_text[:50]}...")
        query_vector = await embedding_service.embed_query(query_text)
        
        if not query_vector:
            logger.error("查询向量化失败")
            return []
        
        # 3. 获取用户可访问的标签
        accessible_tags = await permission_service.get_user_accessible_tags(db, user)
        logger.info(f"用户可访问的标签: {accessible_tags}")
        
        # 4. 构建权限过滤条件
        permission_filters = permission_service.build_elasticsearch_permission_filters(
            user_id=user.id,
            accessible_tags=accessible_tags
        )
        logger.info(f"构建的权限过滤条件 ({len(permission_filters)} 个): {permission_filters}")
        
        # 5. 构建混合检索查询
        es_query = SearchService.build_hybrid_query(
            query_vector=query_vector,
            query_text=query_text,
            permission_filters=permission_filters
        )
        
        # 6. 执行Elasticsearch查询
        logger.info(f"执行混合检索，top_k={top_k}")
        try:
            search_result = await es_client.search(
                index=SearchService.INDEX_NAME,
                query=es_query["query"],
                size=top_k
            )
        except Exception as e:
            logger.error(f"Elasticsearch查询执行失败: {e}", exc_info=True)
            # 如果查询失败，尝试只使用全文检索（不使用向量）
            logger.info("尝试降级为纯全文检索...")
            fallback_query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "text_content": {
                                        "query": query_text,
                                        "boost": 1.0
                                    }
                                }
                            }
                        ],
                        "filter": [
                            {
                                "bool": {
                                    "should": permission_filters,  # 权限条件使用 OR 关系
                                    "minimum_should_match": 1
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            try:
                search_result = await es_client.search(
                    index=SearchService.INDEX_NAME,
                    query=fallback_query["query"],
                    size=top_k
                )
            except Exception as e2:
                logger.error(f"降级查询也失败: {e2}")
                return []
        
        if not search_result:
            logger.warning("Elasticsearch查询返回空结果")
            # 检查索引中是否有任何数据
            try:
                count_result = await es_client.search(
                    index=SearchService.INDEX_NAME,
                    query={"match_all": {}},
                    size=0  # 只获取总数，不返回文档
                )
                
                # 检查 count_result 是否为 None
                if not count_result:
                    logger.error("无法连接到 Elasticsearch 或索引不存在")
                    logger.error("请检查：")
                    logger.error("  1. Elasticsearch 服务是否运行")
                    logger.error("  2. 索引是否已创建（运行 test_upload_knowledge_base.py）")
                    return []
                
                total = count_result.get("hits", {}).get("total", {})
                if isinstance(total, dict):
                    total_count = total.get("value", 0)
                else:
                    total_count = total
                logger.warning(f"索引中总文档数: {total_count}")
                if total_count == 0:
                    logger.warning("  索引中没有数据，请先运行 test_upload_knowledge_base.py 上传文件")
                else:
                    logger.warning(f"  索引中有 {total_count} 个文档，但权限过滤后无匹配结果")
                    logger.warning(f"  用户ID: {user.id}, 可访问标签: {accessible_tags}")
                    logger.warning(f"  权限过滤条件: {permission_filters}")
            except Exception as e:
                logger.error(f"检查索引数据时出错: {e}", exc_info=True)
            return []
        
        # 7. 解析搜索结果
        hits = search_result.get("hits", {}).get("hits", [])
        logger.info(f"Elasticsearch返回 {len(hits)} 个匹配结果")
        
        if not hits:
            logger.warning("Elasticsearch查询返回空结果，可能的原因:")
            # 检查索引中是否有任何数据
            try:
                count_result = await es_client.search(
                    index=SearchService.INDEX_NAME,
                    query={"match_all": {}},
                    size=0
                )
                
                # 检查 count_result 是否为 None
                if not count_result:
                    logger.error("  无法连接到 Elasticsearch 或索引不存在")
                    return []
                
                total = count_result.get("hits", {}).get("total", {})
                if isinstance(total, dict):
                    total_count = total.get("value", 0)
                else:
                    total_count = total
                logger.warning(f"  索引中总文档数: {total_count}")
                if total_count == 0:
                    logger.warning("  索引中没有数据，请先运行 test_upload_knowledge_base.py 上传文件")
                else:
                    logger.warning(f"  索引中有 {total_count} 个文档，但权限过滤后无匹配结果")
                    logger.warning(f"  用户ID: {user.id}, 可访问标签: {accessible_tags}")
                    logger.warning(f"  权限过滤条件: {permission_filters}")
            except Exception as e:
                logger.error(f"检查索引数据时出错: {e}", exc_info=True)
        
        results = []
        
        # 提取所有file_md5，用于批量查询数据库
        file_md5s = set()
        for hit in hits:
            source = hit.get("_source", {})
            file_md5 = source.get("file_md5")
            if file_md5:
                file_md5s.add(file_md5)
        
        # 批量查询文件元数据
        file_metadata = {}
        if file_md5s:
            file_result = await db.execute(
                select(FileUpload).where(FileUpload.file_md5.in_(file_md5s))
            )
            files = file_result.scalars().all()
            file_metadata = {file.file_md5: file for file in files}
        
        # 8. 构建返回结果
        for hit in hits:
            source = hit.get("_source", {})
            score = hit.get("_score", 0.0)
            
            file_md5 = source.get("file_md5")
            chunk_id = source.get("chunk_id")
            text_content = source.get("text_content", "")
            
            # 获取文件名（从数据库或ES中的元数据）
            file_info = file_metadata.get(file_md5)
            file_name = file_info.file_name if file_info else source.get("file_name", "未知文件")
            
            result = {
                "file_md5": file_md5,
                "chunk_id": chunk_id,
                "text_content": text_content,
                "score": round(score, 4),
                "file_name": file_name
            }
            results.append(result)
        
        logger.info(f"混合检索完成，返回 {len(results)} 个结果")
        return results


# 全局服务实例
search_service = SearchService()

