"""
邮箱验证码工具
"""
import random
from app.core.config import settings


def generate_email_code() -> str:
    """生成 6 位数字验证码"""
    return ''.join(random.choices('0123456789', k=settings.EMAIL_CODE_LENGTH))

