"""
FastAPI 应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import router as api_router
from app.core.config import settings
from app.clients.redis_client import redis_client
from app.clients.db_client import db_client
from app.utils.logger import setup_logging, get_logger

# 初始化日志系统
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("=" * 60)
    logger.info("FastAPI 应用启动中...")
    logger.info(f"应用名称: {settings.APP_NAME}")
    logger.info(f"调试模式: {settings.DEBUG}")

    try:
        # 连接数据库
        db_client.connect()
        logger.info("MySQL 数据库连接成功")

        # 连接 Redis
        await redis_client.connect()
        logger.info("Redis 连接成功")

        logger.info("FastAPI 应用启动完成！")
        logger.info("=" * 60)
    except Exception as e:
        logger.critical(f"应用启动失败: {e}", exc_info=True)
        raise

    yield

    # 关闭时
    logger.info("=" * 60)
    logger.info("FastAPI 应用关闭中...")

    try:
        await db_client.close()
        logger.info("MySQL 连接已关闭")

        await redis_client.close()
        logger.info("Redis 连接已关闭")

        logger.info("FastAPI 应用已安全关闭")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"应用关闭时出错: {e}", exc_info=True)


app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI Service",
    version="0.1.0",  # 应用版本号
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


@app.get("/")
async def root():
    """根路径"""
    return {"message": "FastAPI 服务运行中", "docs": "/docs", "redoc": "/redoc"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
