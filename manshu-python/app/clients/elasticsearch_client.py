"""
Elasticsearch 客户端
"""
from elasticsearch import AsyncElasticsearch
from typing import Optional, Dict, List, Any
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ElasticsearchClient:
    """Elasticsearch 异步客户端"""
    
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
    
    async def connect(self):
        """创建 Elasticsearch 客户端连接"""
        try:
            # 构建连接参数
            es_config = {
                "hosts": [settings.ES_HOST],
                "basic_auth": (settings.ES_USER, settings.ES_PASSWORD) if settings.ES_USER else None,
                "verify_certs": settings.ES_VERIFY_CERTS,
                "request_timeout": 30,
                "max_retries": 3,
                "retry_on_timeout": True,
            }
            
            # 如果提供了 API Key，使用 API Key 认证
            if hasattr(settings, 'ES_API_KEY') and settings.ES_API_KEY:
                es_config["api_key"] = settings.ES_API_KEY
                es_config.pop("basic_auth", None)
            
            self.client = AsyncElasticsearch(**es_config)
            
            # 测试连接
            info = await self.client.info()
            logger.info(f"Elasticsearch 客户端初始化成功: {info['version']['number']}")
        except Exception as e:
            logger.error(f"Elasticsearch 客户端初始化失败: {e}")
            raise
    
    async def close(self):
        """关闭 Elasticsearch 客户端"""
        if self.client:
            await self.client.close()
            logger.info("Elasticsearch 连接已关闭")
    
    async def create_index(
        self,
        index: str,
        mappings: Optional[Dict] = None,
        settings: Optional[Dict] = None
    ) -> bool:
        """
        创建索引
        
        Args:
            index: 索引名称
            mappings: 字段映射配置
            settings: 索引设置
            
        Returns:
            bool: 是否创建成功
        """
        try:
            body = {}
            if mappings:
                body["mappings"] = mappings
            if settings:
                body["settings"] = settings
            
            await self.client.indices.create(index=index, body=body)
            logger.info(f"索引创建成功: {index}")
            return True
        except Exception as e:
            logger.error(f"索引创建失败: {e}")
            return False
    
    async def delete_index(self, index: str) -> bool:
        """
        删除索引
        
        Args:
            index: 索引名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            await self.client.indices.delete(index=index)
            logger.info(f"索引删除成功: {index}")
            return True
        except Exception as e:
            logger.error(f"索引删除失败: {e}")
            return False
    
    async def index_exists(self, index: str) -> bool:
        """
        检查索引是否存在
        
        Args:
            index: 索引名称
            
        Returns:
            bool: 索引是否存在
        """
        try:
            return await self.client.indices.exists(index=index)
        except Exception as e:
            logger.error(f"检查索引失败: {e}")
            return False
    
    async def index_document(
        self,
        index: str,
        document: Dict,
        doc_id: Optional[str] = None
    ) -> Optional[str]:
        """
        索引文档（添加或更新）
        
        Args:
            index: 索引名称
            document: 文档数据
            doc_id: 文档 ID（可选，不提供则自动生成）
            
        Returns:
            Optional[str]: 文档 ID，失败返回 None
        """
        try:
            if doc_id:
                result = await self.client.index(index=index, id=doc_id, document=document)
            else:
                result = await self.client.index(index=index, document=document)
            
            logger.info(f"文档索引成功: {index}/{result['_id']}")
            return result["_id"]
        except Exception as e:
            logger.error(f"文档索引失败: {e}")
            return None
    
    async def get_document(self, index: str, doc_id: str) -> Optional[Dict]:
        """
        获取文档
        
        Args:
            index: 索引名称
            doc_id: 文档 ID
            
        Returns:
            Optional[Dict]: 文档数据，失败返回 None
        """
        try:
            result = await self.client.get(index=index, id=doc_id)
            return result["_source"]
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None
    
    async def update_document(
        self,
        index: str,
        doc_id: str,
        document: Dict
    ) -> bool:
        """
        更新文档
        
        Args:
            index: 索引名称
            doc_id: 文档 ID
            document: 要更新的字段
            
        Returns:
            bool: 是否更新成功
        """
        try:
            await self.client.update(index=index, id=doc_id, doc=document)
            logger.info(f"文档更新成功: {index}/{doc_id}")
            return True
        except Exception as e:
            logger.error(f"文档更新失败: {e}")
            return False
    
    async def delete_document(self, index: str, doc_id: str) -> bool:
        """
        删除文档
        
        Args:
            index: 索引名称
            doc_id: 文档 ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            await self.client.delete(index=index, id=doc_id)
            logger.info(f"文档删除成功: {index}/{doc_id}")
            return True
        except Exception as e:
            logger.error(f"文档删除失败: {e}")
            return False
    
    async def search(
        self,
        index: str,
        query: Dict,
        size: int = 10,
        from_: int = 0,
        sort: Optional[List] = None
    ) -> Optional[Dict]:
        """
        搜索文档
        
        Args:
            index: 索引名称
            query: 查询条件
            size: 返回结果数量
            from_: 分页起始位置
            sort: 排序条件
            
        Returns:
            Optional[Dict]: 搜索结果，失败返回 None
        """
        try:
            body = {"query": query, "size": size, "from": from_}
            if sort:
                body["sort"] = sort
            
            result = await self.client.search(index=index, body=body)
            return result
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return None
    
    async def bulk_index(self, index: str, documents: List[Dict]) -> bool:
        """
        批量索引文档
        
        Args:
            index: 索引名称
            documents: 文档列表，每个文档应包含 _id（可选）和 _source
            
        Returns:
            bool: 是否成功
        """
        try:
            from elasticsearch.helpers import async_bulk
            
            # 构建批量操作
            actions = []
            for doc in documents:
                action = {
                    "_index": index,
                    "_source": doc.get("_source", doc)
                }
                if "_id" in doc:
                    action["_id"] = doc["_id"]
                actions.append(action)
            
            success, failed = await async_bulk(self.client, actions)
            logger.info(f"批量索引完成: 成功 {success}, 失败 {failed}")
            return failed == 0
        except Exception as e:
            logger.error(f"批量索引失败: {e}")
            return False
    
    async def count(self, index: str, query: Optional[Dict] = None) -> Optional[int]:
        """
        统计文档数量
        
        Args:
            index: 索引名称
            query: 查询条件（可选）
            
        Returns:
            Optional[int]: 文档数量，失败返回 None
        """
        try:
            body = {"query": query} if query else None
            result = await self.client.count(index=index, body=body)
            return result["count"]
        except Exception as e:
            logger.error(f"统计文档数量失败: {e}")
            return None
    
    async def refresh_index(self, index: str) -> bool:
        """
        刷新索引（使最近的更改可搜索）
        
        Args:
            index: 索引名称
            
        Returns:
            bool: 是否成功
        """
        try:
            await self.client.indices.refresh(index=index)
            return True
        except Exception as e:
            logger.error(f"刷新索引失败: {e}")
            return False
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            health = await self.client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Elasticsearch 健康检查失败: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """获取 Elasticsearch 状态"""
        if not self.client:
            return {"error": "Elasticsearch 客户端未初始化"}
        
        try:
            info = await self.client.info()
            health = await self.client.cluster.health()
            stats = await self.client.cluster.stats()
            
            return {
                "状态": health["status"],
                "版本": info["version"]["number"],
                "集群名称": health["cluster_name"],
                "节点数量": health["number_of_nodes"],
                "数据节点数量": health["number_of_data_nodes"],
                "活跃分片": health["active_shards"],
                "索引数量": stats["indices"]["count"],
                "文档总数": stats["indices"]["docs"]["count"],
                "存储大小": stats["indices"]["store"]["size_in_bytes"]
            }
        except Exception as e:
            return {
                "状态": "连接失败",
                "错误": str(e)
            }


# 全局 Elasticsearch 客户端实例
es_client = ElasticsearchClient()

