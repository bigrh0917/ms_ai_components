"""
管理员相关 Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.schemas.base import BaseResponse


class CreateOrgTagRequest(BaseModel):
    """创建组织标签请求"""
    tagId: str = Field(..., min_length=1, max_length=50, description="标签ID，唯一")
    name: str = Field(..., min_length=1, max_length=100, description="标签名称")
    description: Optional[str] = Field(None, description="标签描述")
    parentTag: Optional[str] = Field(None, max_length=50, description="父标签ID（可选）")


class CreateOrgTagResponse(BaseResponse[Optional[Dict[str, Any]]]):
    """创建组织标签响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Organization tag created successfully", description="提示信息")


class AssignOrgTagsRequest(BaseModel):
    """为用户分配组织标签请求"""
    userId: int = Field(..., description="用户ID")
    orgTags: List[str] = Field(..., min_items=0, description="组织标签列表")


class AssignOrgTagsResponse(BaseResponse[Optional[Dict[str, Any]]]):
    """分配组织标签响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Organization tags assigned successfully", description="提示信息")


class SetPrimaryOrgRequest(BaseModel):
    """设置用户主组织请求"""
    userId: int = Field(..., description="用户ID")
    primaryOrg: str = Field(..., min_length=1, max_length=50, description="主组织标签ID")


class SetPrimaryOrgResponse(BaseResponse[Optional[Dict[str, Any]]]):
    """设置主组织响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Primary organization set successfully", description="提示信息")


# ========== 获取用户组织标签详情 ==========
class OrgTagDetail(BaseModel):
    """组织标签详情"""
    tagId: str
    name: str
    description: Optional[str] = None


class UserOrgTagsData(BaseModel):
    """用户组织标签数据"""
    orgTags: List[str]
    primaryOrg: Optional[str] = None
    orgTagDetails: List[OrgTagDetail]


class UserOrgTagsResponse(BaseResponse[UserOrgTagsData]):
    """用户组织标签响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Get user organization tags successful", description="提示信息")


# ========== 组织标签树 ==========
class OrgTagTreeNode(BaseModel):
    """组织标签树节点"""
    tagId: str
    name: str
    description: Optional[str] = None
    children: List["OrgTagTreeNode"] = []


class OrgTagTreeResponse(BaseResponse[List[OrgTagTreeNode]]):
    """组织标签树响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Get organization tag tree successful", description="提示信息")


# ========== 更新组织标签 ==========
class UpdateOrgTagRequest(BaseModel):
    """更新组织标签请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="新标签名称")
    description: Optional[str] = Field(None, description="新标签描述")
    parentTag: Optional[str] = Field(None, max_length=50, description="新父标签ID（可选）")


class UpdateOrgTagResponse(BaseResponse[Optional[Dict[str, Any]]]):
    """更新组织标签响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Organization tag updated successfully", description="提示信息")


# ========== 删除组织标签 ==========
class DeleteOrgTagResponse(BaseResponse[Optional[Dict[str, Any]]]):
    """删除组织标签响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("Organization tag deleted successfully", description="提示信息")

