"""
API 路由
"""
from fastapi import APIRouter
from app.api.v1 import router as v1_router

router = APIRouter(prefix="/api")

# 注册 v1 版本路由
router.include_router(v1_router, prefix="/v1")

