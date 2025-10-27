"""
Redis 客户端（连接池模式）
"""
import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from typing import Optional
from app.core.config import settings


class RedisClient:
    """Redis 异步客户端（使用连接池）"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.pool: Optional[ConnectionPool] = None
    
    async def connect(self):
        """创建 Redis 连接池"""
        # 创建连接池
        self.pool = ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10,        # 最大连接数
            socket_connect_timeout=5,  # 连接超时（秒）
            socket_keepalive=True,     # 启用 TCP keepalive
            health_check_interval=30,  # 健康检查间隔（秒）
        )
        
        # 使用连接池创建 Redis 客户端
        self.redis = aioredis.Redis(connection_pool=self.pool)
    
    async def close(self):
        """关闭连接池"""
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()
    
    async def set(self, key: str, value: str, expire: int = None) -> bool:
        """设置键值"""
        try:
            if expire:
                await self.redis.setex(key, expire, value)
            else:
                await self.redis.set(key, value)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        try:
            return await self.redis.get(key)
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """删除键"""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False
    
    async def incr(self, key: str, expire: int = None) -> int:
        """递增计数器"""
        try:
            count = await self.redis.incr(key)
            if expire and count == 1:  # 首次设置过期时间
                await self.redis.expire(key, expire)
            return count
        except Exception as e:
            print(f"Redis incr error: {e}")
            return 0
    
    async def ttl(self, key: str) -> int:
        """获取键的剩余生存时间（秒）"""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            print(f"Redis ttl error: {e}")
            return -1
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            print(f"Redis 健康检查失败: {e}")
            return False
    
    def get_pool_status(self) -> dict:
        """获取连接池状态"""
        if not self.pool:
            return {"error": "Redis 连接池未初始化"}
        
        # 获取连接池的内部状态
        pool = self.pool
        
        return {
            "最大连接数": pool.max_connections,
            "当前活跃连接数": len(pool._in_use_connections) if hasattr(pool, '_in_use_connections') else "N/A",
            "可用连接数": len(pool._available_connections) if hasattr(pool, '_available_connections') else "N/A",
            "连接池状态": "healthy" if self.pool else "not initialized",
            "配置": {
                "host": pool.connection_kwargs.get('host'),
                "port": pool.connection_kwargs.get('port'),
                "db": pool.connection_kwargs.get('db'),
                "max_connections": pool.max_connections,
            }
        }


# 全局 Redis 客户端实例
redis_client = RedisClient()

