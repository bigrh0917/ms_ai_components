"""
应用配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path

# 项目根目录（rag 目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "RAG API"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    TEMP_TOKEN_EXPIRE_MINUTES: int = 5
    
    # CORS 配置（开发环境允许所有源）
    CORS_ORIGINS: List[str] = ["*"]  # 或从环境变量读取
    
    # 数据库配置
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = "123456"
    DATABASE_NAME: str = "fastapi"
    
    @property
    def DATABASE_URL(self) -> str:
        """动态构建数据库连接 URL"""
        return f"mysql+aiomysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # 验证码配置
    CAPTCHA_LENGTH: int = 4
    CAPTCHA_EXPIRE_SECONDS: int = 120
    EMAIL_CODE_LENGTH: int = 6
    EMAIL_CODE_EXPIRE_SECONDS: int = 300
    
    # 速率限制配置（统一管理）
    RATE_LIMITS: dict = {
        "captcha": {"limit": 10, "window": 60},       # 图形验证码：每IP每60秒最多10次
        "email_code": {"limit": 3, "window": 60},     # 邮箱验证码：每邮箱每60秒最多3次
        "register": {"limit": 5, "window": 3600}      # 注册：每IP每3600秒(1小时)最多5次
    }

    # 邮件配置
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-app-password"
    SMTP_FROM_EMAIL: str = "your-email@gmail.com"
    SMTP_FROM_NAME: str = "RAG API"
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),  # 使用绝对路径
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 忽略 .env 中的额外字段
    )


settings = Settings()

