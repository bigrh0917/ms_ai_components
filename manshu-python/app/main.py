"""
FastAPI 应用入口
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
from app.api import router as api_router
from app.core.config import settings
from app.core.exceptions import BusinessException
from app.clients.redis_client import redis_client
from app.clients.db_client import db_client
from app.clients.minio_client import minio_client
from app.clients.elasticsearch_client import es_client
from app.clients.kafka_client import kafka_client
from app.services.document_processor_service import document_processor_service
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

    kafka_consumer_task = None
    kafka_consumer = None

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

        # 启动 Kafka 消费者（文档处理）
        try:
            kafka_consumer = await kafka_client.create_consumer(
                topics=["document_parse"],
                group_id="document_processor_group",
                auto_offset_reset='latest',  # 从最新消息开始消费
                enable_auto_commit=True
            )
            
            # 在后台启动消费者任务
            async def consume_loop():
                """消费者循环"""
                try:
                    logger.info("Kafka 消费者已启动，监听 document_parse 主题")
                    await kafka_client.consume_messages(
                        consumer=kafka_consumer,
                        callback=document_processor_service.handle_kafka_message
                    )
                except asyncio.CancelledError:
                    logger.info("Kafka 消费者任务已取消")
                except Exception as e:
                    logger.error(f"Kafka 消费者异常: {e}", exc_info=True)
            
            kafka_consumer_task = asyncio.create_task(consume_loop())
            logger.info("Kafka 文档处理消费者已启动")
            
        except Exception as e:
            logger.warning(f"启动 Kafka 消费者失败（可选服务）: {e}")
            logger.warning("文档处理功能将不可用，但应用可以继续运行")

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
        # 停止 Kafka 消费者任务
        if kafka_consumer_task and not kafka_consumer_task.done():
            logger.info("正在停止 Kafka 消费者...")
            kafka_consumer_task.cancel()
            try:
                await asyncio.wait_for(kafka_consumer_task, timeout=5.0)
            except asyncio.CancelledError:
                logger.info("Kafka 消费者任务已停止")
            except asyncio.TimeoutError:
                logger.warning("Kafka 消费者停止超时")
        
        # 停止消费者
        if kafka_consumer:
            try:
                await kafka_consumer.stop()
                logger.info("Kafka 消费者已停止")
            except Exception as e:
                logger.warning(f"停止 Kafka 消费者时出错: {e}")

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
    """基础健康检查"""
    return {"status": "healthy"}


@app.get("/health/detailed")
async def detailed_health_check():
    """
    详细健康检查 - 包括所有服务状态和连接池监控
    
    返回:
        - 数据库连接池状态
        - Redis连接状态
        - Elasticsearch连接状态
        - MinIO连接状态
        - Kafka连接状态（如果启用）
    """
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    overall_healthy = True
    
    # 数据库连接池状态
    try:
        if not db_client.SessionLocal:
            health_status["services"]["database"] = {
                "status": "uninitialized",
                "error": "数据库未初始化"
            }
            overall_healthy = False
        else:
            db_health = await db_client.health_check()
            db_pool_status = db_client.get_pool_status()
            health_status["services"]["database"] = {
                "status": "healthy" if db_health else "unhealthy",
                "connection_pool": db_pool_status
            }
            if not db_health:
                overall_healthy = False
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        overall_healthy = False
    
    # Redis连接状态
    try:
        if not redis_client.redis:
            health_status["services"]["redis"] = {
                "status": "uninitialized",
                "error": "Redis未初始化"
            }
            overall_healthy = False
        else:
            redis_health = await redis_client.health_check()
            redis_pool_status = redis_client.get_pool_status()
            health_status["services"]["redis"] = {
                "status": "healthy" if redis_health else "unhealthy",
                "connection_pool": redis_pool_status
            }
            if not redis_health:
                overall_healthy = False
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "error",
            "error": str(e)
        }
        overall_healthy = False
    
    # Elasticsearch连接状态
    try:
        if not es_client.client:
            health_status["services"]["elasticsearch"] = {
                "status": "uninitialized",
                "error": "Elasticsearch未初始化"
            }
            overall_healthy = False
        else:
            es_health = await es_client.health_check()
            health_status["services"]["elasticsearch"] = {
                "status": "healthy" if es_health else "unhealthy"
            }
            if not es_health:
                overall_healthy = False
    except Exception as e:
        health_status["services"]["elasticsearch"] = {
            "status": "error",
            "error": str(e)
        }
        overall_healthy = False
    
    # MinIO连接状态
    try:
        if not minio_client.client:
            health_status["services"]["minio"] = {
                "status": "uninitialized",
                "error": "MinIO未初始化"
            }
            overall_healthy = False
        else:
            minio_health = minio_client.health_check()
            minio_status = minio_client.get_status()
            health_status["services"]["minio"] = {
                "status": "healthy" if minio_health else "unhealthy",
                "details": minio_status
            }
            if not minio_health:
                overall_healthy = False
    except Exception as e:
        health_status["services"]["minio"] = {
            "status": "error",
            "error": str(e)
        }
        overall_healthy = False
    
    # Kafka连接状态（可选）
    try:
        if not kafka_client.producer:
            health_status["services"]["kafka"] = {
                "status": "uninitialized",
                "error": "Kafka未初始化"
            }
            # Kafka 失败不影响整体健康状态（可选服务）
        else:
            kafka_health = await kafka_client.health_check()
            health_status["services"]["kafka"] = {
                "status": "healthy" if kafka_health else "unhealthy"
            }
            # Kafka 失败不影响整体健康状态（可选服务）
    except Exception as e:
        health_status["services"]["kafka"] = {
            "status": "error",
            "error": str(e)
        }
        # Kafka 失败不影响整体健康状态（可选服务）
    
    health_status["status"] = "healthy" if overall_healthy else "degraded"
    
    return health_status
