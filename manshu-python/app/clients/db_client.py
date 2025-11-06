"""
MySQL 数据库客户端
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
from app.core.config import settings


class DatabaseClient:
    """MySQL 异步数据库客户端"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
    
    def connect(self):
        """创建数据库引擎和会话工厂"""
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            try:
                # 关闭数据库引擎和连接池
                # 注意：在事件循环关闭时可能会抛出异常，这是正常的
                # 使用 dispose(close=True) 确保所有连接都被关闭
                await self.engine.dispose(close=True)
            except (asyncio.CancelledError, RuntimeError) as e:
                # 忽略取消错误和事件循环已关闭的错误
                # 这些错误在测试结束时是正常的，不影响功能
                # RuntimeError 可能包含 "Event loop is closed"
                pass
            except AttributeError:
                # 忽略属性错误（引擎可能已经被部分清理）
                pass
            except Exception:
                # 忽略其他关闭时的异常
                pass
            finally:
                # 清理引用，确保即使出现异常也能清理
                self.engine = None
                self.SessionLocal = None
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        if not self.SessionLocal:
            raise RuntimeError("数据库未连接，请先调用 connect()")
        
        async with self.SessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with self.SessionLocal() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                return True
        except Exception as e:
            print(f"数据库健康检查失败: {e}")
            return False
    
    def get_pool_status(self) -> dict:
        """获取连接池状态"""
        if not self.engine:
            return {"error": "数据库引擎未初始化"}
        
        pool = self.engine.pool
        return {
            "数据库连接池大小": pool.size(),              # 当前连接池中的连接数
            "数据库连接池可用连接数": pool.checkedin(),        # 可用连接数（空闲连接）
            "数据库连接池正在使用的连接数": pool.checkedout(),      # 正在使用的连接数
            "数据库连接池溢出连接数": pool.overflow(),           # 当前溢出连接数（超过 pool_size 的额外连接）
            "数据库连接池总连接数": pool.size() + pool.overflow(),  # 总连接数
            "数据库连接池状态": "healthy" if pool.checkedin() > 0 else "busy"  # 连接池状态
        }


# 全局数据库客户端实例
db_client = DatabaseClient()

