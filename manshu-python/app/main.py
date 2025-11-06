"""
FastAPI 应用入口
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from app.api import router as api_router
from app.core.config import settings
from app.core.exceptions import BusinessException
from app.clients.redis_client import redis_client
from app.clients.db_client import db_client
from app.clients.minio_client import minio_client
from app.clients.elasticsearch_client import es_client
from app.clients.kafka_client import kafka_client
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

        # 连接 MinIO
        minio_client.connect()
        logger.info("MinIO 对象存储连接成功")

        # 连接 Elasticsearch
        await es_client.connect()
        logger.info("Elasticsearch 连接成功")

        # 连接 Kafka
        await kafka_client.connect()
        logger.info("Kafka 连接成功")

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

        minio_client.close()
        logger.info("MinIO 连接已关闭")

        await es_client.close()
        logger.info("Elasticsearch 连接已关闭")

        await kafka_client.close()
        logger.info("Kafka 连接已关闭")

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

# 业务异常处理器
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器"""
    logger.warning(
        f"业务异常: {exc.code} - {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "code": exc.code,
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": exc.code,
            "message": exc.message,
            "data": exc.data
        }
    )


# HTTP 异常处理器
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 异常处理器"""
    logger.warning(
        f"HTTP 异常: {exc.status_code} - {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
        }
    )
    # 401 错误返回统一格式（code 为数字）
    if exc.status_code == 401:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail if exc.detail else "Unauthorized"
            }
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "data": None
        }
    )

# 请求参数验证异常处理器 Pydantic 模型验证错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数验证异常处理器"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"请求参数验证失败: {errors}",
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "code": "VALIDATION_ERROR",
            "message": "请求参数验证失败",
            "data": {"errors": errors}
        }
    )

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(
        f"未捕获的异常: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "code": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误" if not settings.DEBUG else str(exc),
            "data": None
        }
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
