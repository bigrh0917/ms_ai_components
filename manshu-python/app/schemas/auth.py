"""
认证相关的 Pydantic 模型（已与当前 User 模型对齐）
"""
from pydantic import BaseModel, EmailStr, Field, constr
from datetime import datetime
from typing import Optional, Literal, List
from app.schemas.base import BaseResponse


# ========== 图形验证码 ==========
class CaptchaData(BaseModel):
    """图形验证码数据"""
    captcha_id: str = Field(..., description="验证码ID")
    captcha_image: str = Field(..., description="Base64编码的图片")


class CaptchaResponse(BaseResponse[CaptchaData]):
    """图形验证码响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取验证码成功", description="提示信息")


# ========== 发送邮箱验证码 ==========
class SendEmailCodeRequest(BaseModel):
    """发送邮箱验证码请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    captcha_id: str = Field(..., description="图形验证码ID")
    captcha_code: str = Field(..., min_length=4, max_length=6, description="图形验证码")


class SendEmailCodeData(BaseModel):
    """发送邮箱验证码数据"""
    temp_token: str = Field(..., description="临时令牌")


class SendEmailCodeResponse(BaseResponse[SendEmailCodeData]):
    """发送邮箱验证码响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("验证码已发送到您的邮箱，有效期5分钟", description="提示信息")


# ========== 用户注册 ==========
class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: constr(min_length=3, max_length=50) = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: constr(min_length=6, max_length=50) = Field(..., description="密码")
    email_code: constr(min_length=6, max_length=6) = Field(..., description="邮箱验证码")
    temp_token: str = Field(..., description="临时令牌")


class UserRegisterData(BaseModel):
    """用户注册数据"""
    id: int
    username: str
    email: EmailStr
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer")


class UserRegisterResponse(BaseResponse[UserRegisterData]):
    """用户注册响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("注册成功", description="提示信息")


# ========== 用户登录 ==========
class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str


class UserLoginData(BaseModel):
    """用户登录数据"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: EmailStr


class UserLoginResponse(BaseResponse[UserLoginData]):
    """用户登录响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("登录成功", description="提示信息")


# ========== 用户信息 ==========
class UserResponse(BaseModel):
    """用户响应（与 User 模型字段对齐）"""
    id: int
    username: str
    email: EmailStr
    role: Literal["USER", "ADMIN"]
    org_tags: Optional[str] = None
    primary_org: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ========== 获取用户信息 ==========
class UserInfoData(BaseModel):
    """用户信息数据"""
    id: int
    username: str
    role: str
    orgTags: List[str]
    primaryOrg: Optional[str] = None


class UserInfoResponse(BaseResponse[UserInfoData]):
    """用户信息响应（统一格式）"""
    code: int = Field(200, description="状态码")
    message: str = Field("Success", description="提示信息")


# ========== 用户列表查询 ==========
class UserListItem(BaseModel):
    """用户列表项"""
    userId: int  # 使用 id
    username: str
    email: str
    orgTags: List[str]
    primaryOrg: Optional[str] = None
    createTime: datetime


class UserListContent(BaseModel):
    """用户列表内容"""
    content: List[UserListItem]
    totalElements: int
    totalPages: int
    size: int
    number: int  # 当前页码（从 0 开始）


class UserListResponse(BaseResponse[UserListContent]):
    """用户列表响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Get users successful", description="提示信息")

