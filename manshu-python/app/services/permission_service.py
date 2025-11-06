"""
权限服务 - 处理文档访问权限验证
"""
from typing import List, Set, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserRole
from app.models.organization import OrganizationTag
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PermissionService:
    """权限服务"""
    
    # 默认标签，全局可访问
    DEFAULT_TAG = "DEFAULT"
    
    @staticmethod
    async def get_all_descendant_tags(
        db: AsyncSession,
        tag_id: str
    ) -> Set[str]:
        """
        获取标签的所有后代标签（包括子标签、孙标签等）
        
        Args:
            db: 数据库会话
            tag_id: 标签ID
            
        Returns:
            包含自身和所有后代标签ID的集合
        """
        result_tags = {tag_id}
        
        # 递归查找所有子标签
        async def find_children(parent_id: str):
            """递归查找子标签"""
            result = await db.execute(
                select(OrganizationTag).where(OrganizationTag.parent_tag == parent_id)
            )
            children = result.scalars().all()
            
            for child in children:
                if child.tag_id not in result_tags:
                    result_tags.add(child.tag_id)
                    # 递归查找子标签的子标签
                    await find_children(child.tag_id)
        
        await find_children(tag_id)
        
        return result_tags
    
    @staticmethod
    async def get_user_accessible_tags(
        db: AsyncSession,
        user: User
    ) -> Set[str]:
        """
        获取用户可访问的所有标签（包括层级展开）
        
        Args:
            db: 数据库会话
            user: 用户对象
            
        Returns:
            用户可访问的所有标签ID集合（包括自身标签和所有子标签）
        """
        accessible_tags = set()
        
        # 1. 添加默认标签（全局可访问）
        accessible_tags.add(PermissionService.DEFAULT_TAG)
        
        # 2. 解析用户的组织标签
        if user.org_tags:
            user_tags = [tag.strip() for tag in user.org_tags.split(",") if tag.strip()]
            
            for tag_id in user_tags:
                accessible_tags.add(tag_id)
                # 获取该标签的所有子标签
                descendant_tags = await PermissionService.get_all_descendant_tags(db, tag_id)
                accessible_tags.update(descendant_tags)
        
        logger.debug(f"用户 {user.id} 可访问的标签: {accessible_tags}")
        return accessible_tags
    
    @staticmethod
    def build_elasticsearch_permission_filters(
        user_id: int,
        accessible_tags: Set[str],
        include_default: bool = True
    ) -> List[dict]:
        """
        构建Elasticsearch权限过滤条件
        
        Args:
            user_id: 用户ID
            accessible_tags: 用户可访问的标签集合
            include_default: 是否包含默认标签（通常为True）
            
        Returns:
            Elasticsearch filter条件列表
        """
        filters = []
        
        # 1. 用户自己上传的文档
        filters.append({
            "term": {"user_id": user_id}
        })
        
        # 2. 公开的文档
        filters.append({
            "term": {"is_public": True}
        })
        
        # 3. 默认标签的文档（全局可访问）
        if include_default:
            filters.append({
                "term": {"org_tag": PermissionService.DEFAULT_TAG}
            })
        
        # 4. 用户有权限的组织标签的文档
        if accessible_tags:
            # 排除DEFAULT（已在上面单独处理）
            org_tags = [tag for tag in accessible_tags if tag != PermissionService.DEFAULT_TAG]
            if org_tags:
                filters.append({
                    "terms": {"org_tag": org_tags}
                })
        
        logger.debug(f"构建的权限过滤条件数量: {len(filters)}")
        return filters
    
    @staticmethod
    async def check_file_access_permission(
        db: AsyncSession,
        user: User,
        file_user_id: int,
        file_org_tag: Optional[str],
        file_is_public: bool
    ) -> bool:
        """
        检查用户是否有权限访问指定文件
        
        Args:
            db: 数据库会话
            user: 用户对象
            file_user_id: 文件上传者ID
            file_org_tag: 文件所属组织标签
            file_is_public: 文件是否公开
            
        Returns:
            True表示有权限，False表示无权限
        """
        # 管理员可以访问所有文件
        if user.role == UserRole.ADMIN:
            return True
        
        # 1. 用户自己上传的文档
        if file_user_id == user.id:
            return True
        
        # 2. 公开的文档
        if file_is_public:
            return True
        
        # 3. 默认标签的文档（全局可访问）
        if file_org_tag == PermissionService.DEFAULT_TAG:
            return True
        
        # 4. 用户有权限的组织标签的文档（包括层级）
        if file_org_tag:
            accessible_tags = await PermissionService.get_user_accessible_tags(db, user)
            # 检查文件标签是否在用户可访问的标签集合中（包括层级展开）
            if file_org_tag in accessible_tags:
                return True
        
        return False
    
    @staticmethod
    async def check_file_delete_permission(
        user: User,
        file_user_id: int
    ) -> bool:
        """
        检查用户是否有权限删除指定文件
        
        Args:
            user: 用户对象
            file_user_id: 文件上传者ID
            
        Returns:
            True表示有权限，False表示无权限
            
        Note:
            文件所有者或管理员可以删除文件
        """
        # 管理员可以删除任何文件
        if user.role == UserRole.ADMIN:
            return True
        
        # 文件所有者可以删除
        return file_user_id == user.id


# 全局服务实例
permission_service = PermissionService()

