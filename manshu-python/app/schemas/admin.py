"""
管理员相关 Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class CreateOrgTagRequest(BaseModel):
    """创建组织标签请求"""
    tagId: str = Field(..., min_length=1, max_length=50, description="标签ID，唯一")
    name: str = Field(..., min_length=1, max_length=100, description="标签名称")
    description: Optional[str] = Field(None, description="标签描述")
    parentTag: Optional[str] = Field(None, max_length=50, description="父标签ID（可选）")


class CreateOrgTagResponse(BaseModel):
    """创建组织标签响应"""
    code: int = 200
    message: str = "Organization tag created successfully"


class AssignOrgTagsRequest(BaseModel):
    """为用户分配组织标签请求"""
    userId: int = Field(..., description="用户ID")
    orgTags: List[str] = Field(..., min_items=0, description="组织标签列表")


class AssignOrgTagsResponse(BaseModel):
    """分配组织标签响应"""
    code: int = 200
    message: str = "Organization tags assigned successfully"


class SetPrimaryOrgRequest(BaseModel):
    """设置用户主组织请求"""
    userId: int = Field(..., description="用户ID")
    primaryOrg: str = Field(..., min_length=1, max_length=50, description="主组织标签ID")


class SetPrimaryOrgResponse(BaseModel):
    """设置主组织响应"""
    code: int = 200
    message: str = "Primary organization set successfully"


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


class UserOrgTagsResponse(BaseModel):
    """用户组织标签响应"""
    code: int = 200
    message: str = "Get user organization tags successful"
    data: UserOrgTagsData


# ========== 组织标签树 ==========
class OrgTagTreeNode(BaseModel):
    """组织标签树节点"""
    tagId: str
    name: str
    description: Optional[str] = None
    children: List["OrgTagTreeNode"] = []


class OrgTagTreeResponse(BaseModel):
    """组织标签树响应"""
    code: int = 200
    message: str = "Get organization tag tree successful"
    data: List[OrgTagTreeNode]


# ========== 更新组织标签 ==========
class UpdateOrgTagRequest(BaseModel):
    """更新组织标签请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="新标签名称")
    description: Optional[str] = Field(None, description="新标签描述")
    parentTag: Optional[str] = Field(None, max_length=50, description="新父标签ID（可选）")


class UpdateOrgTagResponse(BaseModel):
    """更新组织标签响应"""
    code: int = 200
    message: str = "Organization tag updated successfully"


# ========== 删除组织标签 ==========
class DeleteOrgTagResponse(BaseModel):
    """删除组织标签响应"""
    code: int = 200
    message: str = "Organization tag deleted successfully"

