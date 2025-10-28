"""
应用配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path

# 项目根目录（rag 目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """应用配置 - 所有配置从 .env 文件读取"""
    
    # 应用配置
    APP_NAME: str
    DEBUG: bool
    API_V1_STR: str
    
    # 安全配置
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    TEMP_TOKEN_EXPIRE_MINUTES: int
    
    # CORS 配置
    CORS_ORIGINS: List[str]
    
    # 数据库配置
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str
    
    @property
    def DATABASE_URL(self) -> str:
        """动态构建数据库连接 URL"""
        return f"mysql+aiomysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
    
    # Redis 配置
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str
    
    # 验证码配置
    CAPTCHA_LENGTH: int
    CAPTCHA_EXPIRE_SECONDS: int
    EMAIL_CODE_LENGTH: int
    EMAIL_CODE_EXPIRE_SECONDS: int
    
    # 速率限制配置 - 从环境变量读取
    RATE_LIMIT_CAPTCHA_LIMIT: int
    RATE_LIMIT_CAPTCHA_WINDOW: int
    RATE_LIMIT_EMAIL_CODE_LIMIT: int
    RATE_LIMIT_EMAIL_CODE_WINDOW: int
    RATE_LIMIT_REGISTER_LIMIT: int
    RATE_LIMIT_REGISTER_WINDOW: int
    
    @property
    def RATE_LIMITS(self) -> dict:
        """动态构建速率限制配置"""
        return {
            "captcha": {
                "limit": self.RATE_LIMIT_CAPTCHA_LIMIT,
                "window": self.RATE_LIMIT_CAPTCHA_WINDOW
            },
            "email_code": {
                "limit": self.RATE_LIMIT_EMAIL_CODE_LIMIT,
                "window": self.RATE_LIMIT_EMAIL_CODE_WINDOW
            },
            "register": {
                "limit": self.RATE_LIMIT_REGISTER_LIMIT,
                "window": self.RATE_LIMIT_REGISTER_WINDOW
            }
        }

    # 邮件配置
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str
    
    # MinIO 配置
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False
    MINIO_DEFAULT_BUCKET: str = "default"
    
    # Elasticsearch 配置
    ES_HOST: str
    ES_USER: str = ""
    ES_PASSWORD: str = ""
    ES_VERIFY_CERTS: bool = False
    ES_DEFAULT_INDEX: str = "default"
    
    # Kafka 配置
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_DEFAULT_TOPIC: str = "default"
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),  # 使用绝对路径
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 忽略 .env 中的额外字段
    )


settings = Settings()

