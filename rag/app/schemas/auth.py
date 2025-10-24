"""
认证相关的 Pydantic 模型
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# ========== 图形验证码 ==========
class CaptchaResponse(BaseModel):
    """图形验证码响应"""
    captcha_id: str = Field(..., description="验证码ID")
    captcha_image: str = Field(..., description="Base64编码的图片")


# ========== 发送邮箱验证码 ==========
class SendEmailCodeRequest(BaseModel):
    """发送邮箱验证码请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    captcha_id: str = Field(..., description="图形验证码ID")
    captcha_code: str = Field(..., min_length=4, max_length=6, description="图形验证码")


class SendEmailCodeResponse(BaseModel):
    """发送邮箱验证码响应"""
    temp_token: str = Field(..., description="临时令牌")
    message: str = Field(default="验证码已发送", description="提示信息")


# ========== 用户注册 ==========
class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    email_code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")
    temp_token: str = Field(..., description="临时令牌")


class UserRegisterResponse(BaseModel):
    """用户注册响应"""
    id: str
    email: EmailStr
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer")
    message: str = Field(default="注册成功")


# ========== 用户登录 ==========
class UserLoginRequest(BaseModel):
    """用户登录请求"""
    email: EmailStr
    password: str


class UserLoginResponse(BaseModel):
    """用户登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: EmailStr


# ========== 用户信息 ==========
class UserResponse(BaseModel):
    """用户响应"""
    id: str
    email: EmailStr
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

