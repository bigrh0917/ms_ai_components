"""
外部服务客户端
"""
from app.clients.redis_client import redis_client
from app.clients.db_client import db_client

__all__ = ['redis_client', 'db_client']

