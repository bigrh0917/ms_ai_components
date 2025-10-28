"""
用户认证接口
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db
from app.utils.logger import get_logger, mask_sensitive

# 创建日志记录器
logger = get_logger(__name__)
from app.schemas.auth import (
    CaptchaResponse,
    SendEmailCodeRequest,
    SendEmailCodeResponse,
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserLoginResponse,
)
from app.models.user import User
from app.clients.redis_client import redis_client
from app.core.config import settings
from app.utils.captcha import generate_captcha_text, generate_captcha_image, verify_captcha
from app.utils.email_code import generate_email_code
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_temp_token,
    verify_temp_token,
    generate_uuid,
)
from app.utils.rate_limit import (
    check_captcha_rate_limit,
    check_email_code_rate_limit,
    check_register_rate_limit,
)
from app.services.email_service import email_service

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
        await redis_client.set(key, captcha_text, expire=settings.CAPTCHA_EXPIRE_SECONDS)
        
        logger.info(f"生成图形验证码成功 | IP: {client_ip} | ID: {captcha_id[:8]}...")
        
        return CaptchaResponse(
            captcha_id=captcha_id,
            captcha_image=captcha_image
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成图形验证码失败 | IP: {client_ip}", exc_info=True)
        raise HTTPException(status_code=500, detail="验证码生成失败")


@router.post("/send_code", response_model=SendEmailCodeResponse)
async def send_email_code(
    request_data: SendEmailCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
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
                detail="图形验证码已过期或不存在"
            )
        
        if not verify_captcha(request_data.captcha_code, stored_captcha):
            logger.warning(f"图形验证码错误 | 邮箱: {masked_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="图形验证码错误"
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该邮箱已被注册"
            )
        
        # 速率限制
        await check_email_code_rate_limit(request_data.email)
        
        # 生成临时 token
        temp_token = create_temp_token(request_data.email)
        
        # 生成邮箱验证码
        email_code = generate_email_code()
        
        # 存入 Redis
        email_code_key = f"email_code:{request_data.email}"
        await redis_client.set(
            email_code_key,
            email_code,
            expire=settings.EMAIL_CODE_EXPIRE_SECONDS
        )
        
        # 异步发送邮件
        background_tasks.add_task(
            email_service.send_verification_code,
            request_data.email,
            email_code
        )
        
        logger.info(f"邮箱验证码发送成功 | 邮箱: {masked_email}")
        
        return SendEmailCodeResponse(
            temp_token=temp_token,
            message="验证码已发送到您的邮箱，有效期5分钟"
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
    db: AsyncSession = Depends(get_db)
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
    email_from_token = verify_temp_token(request_data.temp_token)
    if not email_from_token or email_from_token != request_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="临时令牌无效或已过期"
        )
    
    # 验证邮箱验证码
    email_code_key = f"email_code:{request_data.email}"
    stored_code = await redis_client.get(email_code_key)
    
    if not stored_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱验证码已过期或不存在"
        )
    
    if stored_code != request_data.email_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱验证码错误"
        )
    
    # 删除已使用的验证码
    await redis_client.delete(email_code_key)
    
    # 再次检查邮箱是否已注册（防止并发）
    result = await db.execute(select(User).where(User.email == request_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # 创建用户
    user_id = generate_uuid()
    hashed_pwd = hash_password(request_data.password)
    
    new_user = User(
        id=user_id,
        email=request_data.email,
        hashed_password=hashed_pwd,
        is_active=True,
        is_verified=True,  # 通过邮箱验证后直接设为已验证
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 生成访问 token（自动登录）
    access_token = create_access_token(data={"sub": user_id})
    
    # 清理相关临时数据
    # temp_token 会自动过期，这里可选择性删除
    
    return UserRegisterResponse(
        id=new_user.id,
        email=new_user.email,
        access_token=access_token,
        token_type="bearer",
        message="注册成功"
    )


@router.post("/login", response_model=UserLoginResponse)
async def login(
    request_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    
    - 验证邮箱和密码
    - 返回访问token
    """
    # 查询用户
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    # 验证密码
    if not verify_password(request_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 生成访问 token
    access_token = create_access_token(data={"sub": user.id})
    
    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email
    )


