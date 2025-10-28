"""
API v1 路由
"""
from fastapi import APIRouter
from app.api.v1 import auth_router
from app.api.v1 import document_router
from app.api.v1 import file_router

router = APIRouter()

# 注册子路由
router.include_router(auth_router.router, prefix="/auth", tags=["认证"])
router.include_router(document_router.router, prefix="/document", tags=["文档"])
router.include_router(file_router.router, prefix="/file", tags=["文件"])

