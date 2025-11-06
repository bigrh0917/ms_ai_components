"""
用户认证接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from app.api.deps import get_db, get_current_user
from app.utils.logger import get_logger, mask_sensitive
from app.schemas.auth import (
    CaptchaResponse,
    SendEmailCodeRequest,
    SendEmailCodeResponse,
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserInfoResponse,
    UserInfoData,
    UserListResponse,
    UserListItem,
)
from app.models.user import User, UserRole
from typing import List, Optional
from app.clients.redis_client import redis_client
from app.core.config import settings
from app.utils.captcha import (
    generate_captcha_text,
    generate_captcha_image,
    verify_captcha,
)
from app.utils.email_code import generate_email_code
from app.utils.security import (
    hash_password,
    verify_password,
    generate_uuid,
)
from app.utils import jwt_utils
from app.utils.rate_limit import (
    check_captcha_rate_limit,
    check_email_code_rate_limit,
    check_register_rate_limit,
)
from app.services.email_service import email_service
from app.models.organization import OrganizationTag

# 创建日志记录器
logger = get_logger(__name__)


router = APIRouter()


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha(request: Request):
    """
    获取图形验证码

    - 速率限制：每IP每分钟最多10次
    - 返回：验证码ID + Base64图片
    """
    client_ip = request.client.host
    logger.debug(f"请求图形验证码 | IP: {client_ip}")

    try:
        # 速率限制
        await check_captcha_rate_limit(request)

        # 生成验证码
        captcha_id = generate_uuid()
        captcha_text = generate_captcha_text()
        captcha_image = generate_captcha_image(captcha_text)

        # 存入 Redis
        key = f"captcha:{captcha_id}"
        await redis_client.set(
            key, captcha_text, expire=settings.CAPTCHA_EXPIRE_SECONDS
        )

        logger.info(f"生成图形验证码成功 | IP: {client_ip} | ID: {captcha_id[:8]}...")

        return CaptchaResponse(captcha_id=captcha_id, captcha_image=captcha_image)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成图形验证码失败 | IP: {client_ip}", exc_info=True)
        raise HTTPException(status_code=500, detail="验证码生成失败")


@router.post("/send_code", response_model=SendEmailCodeResponse)
async def send_email_code(
    request_data: SendEmailCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    发送邮箱验证码

    - 验证图形验证码
    - 检查邮箱是否已注册
    - 速率限制：每邮箱每分钟最多3次
    - 生成临时token和邮箱验证码
    - 异步发送邮件
    """
    masked_email = mask_sensitive(request_data.email, visible=3)
    logger.info(f"请求发送验证码 | 邮箱: {masked_email}")

    try:
        # 验证图形验证码
        captcha_key = f"captcha:{request_data.captcha_id}"
        stored_captcha = await redis_client.get(captcha_key)

        if not stored_captcha:
            logger.warning(f"图形验证码已过期 | 邮箱: {masked_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="图形验证码已过期或不存在",
            )

        if not verify_captcha(request_data.captcha_code, stored_captcha):
            logger.warning(f"图形验证码错误 | 邮箱: {masked_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="图形验证码错误"
            )

        # 删除已使用的图形验证码
        await redis_client.delete(captcha_key)
        logger.debug(f"图形验证码验证成功 | 邮箱: {masked_email}")

        # 检查邮箱是否已注册
        result = await db.execute(select(User).where(User.email == request_data.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(f"邮箱已被注册 | 邮箱: {masked_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被注册"
            )

        # 速率限制
        await check_email_code_rate_limit(request_data.email)

        # 生成临时 token（统一由 jwt_utils 提供）
        temp_token = jwt_utils.create_temp_token(request_data.email)

        # 生成邮箱验证码
        email_code = generate_email_code()

        # 存入 Redis
        email_code_key = f"email_code:{request_data.email}"
        await redis_client.set(
            email_code_key, email_code, expire=settings.EMAIL_CODE_EXPIRE_SECONDS
        )

        # 异步发送邮件
        background_tasks.add_task(
            email_service.send_verification_code, request_data.email, email_code
        )

        logger.info(f"邮箱验证码发送成功 | 邮箱: {masked_email}")

        return SendEmailCodeResponse(
            temp_token=temp_token, message="验证码已发送到您的邮箱，有效期5分钟"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送邮箱验证码失败 | 邮箱: {masked_email}", exc_info=True)
        raise HTTPException(status_code=500, detail="发送验证码失败")


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    request_data: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册
    - 验证临时token（防止跳过图形验证）
    - 验证邮箱验证码
    - 创建用户
    - 返回访问token（自动登录）
    """
    # 注册速率限制
    await check_register_rate_limit(request)

    # 验证临时 token
    email_from_token = jwt_utils.verify_temp_token(request_data.temp_token)
    if not email_from_token or email_from_token != request_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="临时令牌无效或已过期"
        )

    # 验证邮箱验证码
    email_code_key = f"email_code:{request_data.email}"
    stored_code = await redis_client.get(email_code_key)

    if not stored_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱验证码已过期或不存在"
        )

    if stored_code != request_data.email_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱验证码错误"
        )

    # 删除已使用的验证码
    await redis_client.delete(email_code_key)

    # 再次检查邮箱是否已注册（防止并发）
    result = await db.execute(select(User).where(User.email == request_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被注册"
        )

    # 额外校验：用户名是否已存在
    result = await db.execute(
        select(User).where(User.username == request_data.username)
    )
    existing_username = result.scalar_one_or_none()
    if existing_username:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建用户和组织标签（原子操作）
    try:
        hashed_pwd = hash_password(request_data.password)
        new_user = User(
            username=request_data.username,
            email=request_data.email,
            password=hashed_pwd,
            role=UserRole.USER,
        )
        db.add(new_user)
        await db.flush()  # 刷新以获取用户ID，但不提交
        
        # 创建用户私人组织标签（PRIVATE_username）
        private_tag_id = f"PRIVATE_{request_data.username}"
        private_tag = OrganizationTag(
            tag_id=private_tag_id,
            name=f"我的组织-{request_data.username}",
            description=f"用户 {request_data.username} 的私人组织",
            parent_tag=None,  # 顶级标签，无父标签
            created_by=new_user.id,
        )
        db.add(private_tag)

        # 设置用户的组织标签和主组织
        new_user.org_tags = private_tag_id
        new_user.primary_org = private_tag_id
        
        # 一次性提交所有更改（原子操作）
        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
        error_type = type(e).__name__
        error_detail = str(e)
        logger.error(f"用户注册失败: {error_type}: {error_detail}", exc_info=True)
        
        # 根据错误类型提供更具体的错误消息
        if "IntegrityError" in error_type or "duplicate" in error_detail.lower():
            detail_msg = "用户名或邮箱已存在，请使用其他信息注册。"
        elif "database" in error_detail.lower() or "Database" in error_type:
            detail_msg = "数据库操作失败，请稍后重试。如果问题持续，请联系管理员。"
        elif "connection" in error_detail.lower() or "Connection" in error_type:
            detail_msg = "无法连接到数据库，请稍后重试。"
        else:
            detail_msg = f"注册失败: {error_detail[:100]}（错误类型: {error_type}）"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail_msg
        )

    # 生成访问 token（使用增强版 JWT 工具，自动写入角色/组织等 claims 并缓存）
    access_token = await jwt_utils.generate_token(db, new_user.username)

    # 清理相关临时数据
    # temp_token 会自动过期，这里可选择性删除

    return UserRegisterResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        access_token=access_token,
        token_type="bearer",
        message="注册成功",
    )


@router.post("/login", response_model=UserLoginResponse)
async def login(request_data: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    用户登录

    - 接收用户登录请求，获取用户名和密码
    - 查询用户记录并验证密码
    - 加载用户组织标签信息（通过 generate_token 自动加载）
    - 生成包含用户信息和组织标签的 JWT Token
    - 返回登录成功响应和 Token
    """
    # 查询用户（按用户名）
    result = await db.execute(select(User).where(User.username == request_data.username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    # 验证密码
    if not verify_password(request_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    # 生成访问 token（增强版）
    access_token = await jwt_utils.generate_token(db, user.username)

    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户信息
    
    - 从 JWT token 中提取用户信息
    - 返回用户详细信息（包含组织标签）
    """
    # 解析组织标签（如果是逗号分隔的字符串，转换为列表）
    org_tags_list: List[str] = []
    if current_user.org_tags:
        org_tags_list = [tag.strip() for tag in current_user.org_tags.split(",") if tag.strip()]
    
    # 获取角色字符串
    role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    
    return UserInfoResponse(
        code=200,
        message="Success",
        data=UserInfoData(
            id=current_user.id,
            username=current_user.username,
            role=role_str,
            orgTags=org_tags_list,
            primaryOrg=current_user.primary_org,
        )
    )


@router.get("/users", response_model=UserListResponse)
async def get_user_list(
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    orgTag: Optional[str] = None,
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户列表
    
    - 支持分页查询
    - 支持关键词搜索（用户名或邮箱）
    - 支持按组织标签筛选
    - 需要 JWT 认证
    """
    # 构建查询
    query = select(User)
    
    # 关键词搜索（用户名或邮箱）
    if keyword:
        query = query.where(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%")
            )
        )
    
    # 组织标签筛选
    if orgTag:
        query = query.where(
            or_(
                User.org_tags.like(f"%{orgTag}%"),
                User.primary_org == orgTag
            )
        )
    
    # 获取总数（使用相同的筛选条件）
    count_query = select(func.count(User.id))
    
    # 应用相同的筛选条件
    if keyword:
        count_query = count_query.where(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%")
            )
        )
    if orgTag:
        count_query = count_query.where(
            or_(
                User.org_tags.like(f"%{orgTag}%"),
                User.primary_org == orgTag
            )
        )
    
    total_result = await db.execute(count_query)
    total_elements = total_result.scalar_one()
    
    # 分页
    offset = (page - 1) * size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(size)
    
    # 执行查询
    result = await db.execute(query)
    users = result.scalars().all()
    
    # 构建响应
    user_items = []
    for user in users:
        # 解析组织标签
        org_tags_list: List[str] = []
        if user.org_tags:
            org_tags_list = [tag.strip() for tag in user.org_tags.split(",") if tag.strip()]
        
        user_items.append(UserListItem(
            userId=user.id,
            username=user.username,
            email=user.email,
            orgTags=org_tags_list,
            primaryOrg=user.primary_org,
            createTime=user.created_at
        ))
    
    # 计算总页数
    total_pages = (total_elements + size - 1) // size if total_elements > 0 else 0
    
    return UserListResponse(
        code=200,
        message="Get users successful",
        data={
            "content": user_items,
            "totalElements": total_elements,
            "totalPages": total_pages,
            "size": size,
            "number": page - 1  # 从 0 开始
        }
    )
