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
    
    - 开发环境：DEBUG 级别，输出到控制台
    - 生产环境：INFO 级别，输出到文件和控制台
    - 自动轮转：每个文件最大 10MB，保留 5 个备份
    """
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
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
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(simple_formatter if settings.DEBUG else detailed_formatter)
    root_logger.addHandler(console_handler)
    
    # ========== 2. 主日志文件（所有级别）==========
    app_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    app_handler.setLevel(logging.INFO)
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
    
    # ========== 4. 按天轮转的日志（可选）==========
    if not settings.DEBUG:
        daily_handler = TimedRotatingFileHandler(
            log_dir / "daily.log",
            when='midnight',
            interval=1,
            backupCount=30,  # 保留 30 天
            encoding='utf-8'
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(daily_handler)
    
    # ========== 配置第三方库日志级别 ==========
    # 降低 uvicorn 的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # 降低 SQLAlchemy 的日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # 保持我们自己的日志级别
    logging.getLogger("app").setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # 初始化日志
    logger = logging.getLogger("app")
    logger.info("=" * 60)
    logger.info(f"日志系统初始化完成 | 环境: {'开发' if settings.DEBUG else '生产'}")
    logger.info(f"日志目录: {log_dir.absolute()}")
    logger.info(f"日志级别: {logging.getLevelName(root_logger.level)}")
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

