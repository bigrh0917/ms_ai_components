"""
API v1 路由
"""
from fastapi import APIRouter
from app.api.v1 import auth

router = APIRouter()

# 注册子路由
router.include_router(auth.router, prefix="/auth", tags=["认证"])


