"""
日志配置模块
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from app.core.config import settings


def setup_logging():
    """
    配置应用日志系统
    
    - 根据DEBUG模式自动选择日志级别（可通过环境变量配置）
    - 开发环境：使用DEBUG_LOG_LEVEL配置（默认DEBUG）
    - 生产环境：使用PRODUCTION_LOG_LEVEL配置（默认INFO）
    - 自动轮转：每个文件最大 10MB，保留 5 个备份
    """
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 获取当前模式的日志级别
    log_level = settings.get_log_level()
    log_level_name = logging.getLevelName(log_level)
    
    # 根 logger - 设置为WARNING，避免处理所有日志（由子logger控制）
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    
    # 清除已有的 handlers（避免重复）
    root_logger.handlers.clear()
    
    # 日志格式
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # ========== 1. 控制台输出 ==========
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    # DEBUG模式使用简单格式，其他使用详细格式
    console_handler.setFormatter(simple_formatter if settings.DEBUG else detailed_formatter)
    root_logger.addHandler(console_handler)
    
    # ========== 2. 主日志文件 ==========
    app_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    app_handler.setLevel(log_level)
    app_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_handler)
    
    # ========== 3. 错误日志文件（只记录 ERROR 及以上）==========
    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # ========== 4. 按天轮转的日志（生产环境）==========
    if not settings.DEBUG:
        daily_handler = TimedRotatingFileHandler(
            log_dir / "daily.log",
            when='midnight',
            interval=1,
            backupCount=30,  # 保留 30 天
            encoding='utf-8'
        )
        daily_handler.setLevel(log_level)
        daily_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(daily_handler)
    
    # ========== 配置第三方库日志级别 ==========
    # 降低 uvicorn 的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # 降低 SQLAlchemy 的日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # ========== 配置应用模块日志级别 ==========
    # app模块使用配置的日志级别
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    app_logger.propagate = True  # 传播到根logger，由根logger的handlers处理
    
    # services模块默认WARNING，减少输出（可在代码中调整）
    services_logger = logging.getLogger("app.services")
    services_logger.setLevel(logging.WARNING)
    services_logger.propagate = True
    
    # 初始化日志
    logger = logging.getLogger("app")
    logger.info("=" * 60)
    logger.info(f"日志系统初始化完成 | 环境: {'开发' if settings.DEBUG else '生产'}")
    logger.info(f"日志目录: {log_dir.absolute()}")
    logger.info(f"日志级别: {log_level_name} (由{'DEBUG_LOG_LEVEL' if settings.DEBUG else 'PRODUCTION_LOG_LEVEL'}配置)")
    logger.info("=" * 60)
    
    return logger


def get_logger(name: str = "app") -> logging.Logger:
    """
    获取 logger 实例
    
    Args:
        name: logger 名称，通常使用 __name__
        
    Returns:
        Logger 实例
        
    Usage:
        logger = get_logger(__name__)
        logger.info("这是一条日志")
    """
    return logging.getLogger(name)


# 便捷函数：记录敏感信息时自动脱敏
def mask_sensitive(value: str, visible: int = 4) -> str:
    """
    脱敏处理
    
    Args:
        value: 原始值
        visible: 显示前几位
        
    Returns:
        脱敏后的字符串
        
    Example:
        mask_sensitive("1234567890") -> "1234******"
        mask_sensitive("user@example.com", 3) -> "use**********"
    """
    if not value:
        return "****"
    
    if len(value) <= visible:
        return "*" * len(value)
    
    return value[:visible] + "*" * (len(value) - visible)

