"""
认证相关的 Pydantic 模型（已与当前 User 模型对齐）
"""
from pydantic import BaseModel, EmailStr, Field, constr
from datetime import datetime
from typing import Optional, Literal, List


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
    username: constr(min_length=3, max_length=50) = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: constr(min_length=6, max_length=50) = Field(..., description="密码")
    email_code: constr(min_length=6, max_length=6) = Field(..., description="邮箱验证码")
    temp_token: str = Field(..., description="临时令牌")


class UserRegisterResponse(BaseModel):
    """用户注册响应"""
    id: int
    username: str
    email: EmailStr
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer")
    message: str = Field(default="注册成功")


# ========== 用户登录 ==========
class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str


class UserLoginResponse(BaseModel):
    """用户登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: EmailStr


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


class UserInfoResponse(BaseModel):
    """用户信息响应（统一格式）"""
    code: int = 200
    message: str = "Success"
    data: UserInfoData


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


class UserListResponse(BaseModel):
    """用户列表响应"""
    code: int = 200
    message: str = "Get users successful"
    data: UserListContent

