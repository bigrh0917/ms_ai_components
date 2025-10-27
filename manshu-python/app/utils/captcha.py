"""
图形验证码工具（使用 Pillow 直接实现）
"""
import random
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.core.config import settings


def generate_captcha_text() -> str:
    """生成随机验证码文本（数字+大写字母，排除易混淆字符）"""
    # 排除易混淆字符: 0, O, 1, I, L
    chars = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'
    return ''.join(random.choices(chars, k=settings.CAPTCHA_LENGTH))


def generate_captcha_image(text: str) -> str:
    """
    生成验证码图片并返回 base64 编码
    
    Args:
        text: 验证码文本
        
    Returns:
        base64 编码的图片字符串
    """
    # 图片尺寸
    width, height = 160, 60
    
    # 创建图片（白色背景）
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 绘制背景干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(
            random.randint(150, 200),
            random.randint(150, 200),
            random.randint(150, 200)
        ), width=1)
    
    # 绘制干扰点
    for _ in range(50):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(
            random.randint(150, 200),
            random.randint(150, 200),
            random.randint(150, 200)
        ))
    
    # 尝试加载字体（如果失败使用默认字体）
    try:
        # Windows 系统字体
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        try:
            # 尝试其他常见字体
            font = ImageFont.truetype("Arial.ttf", 40)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
    
    # 计算文字位置（居中）
    char_width = width // len(text)
    
    # 绘制文字
    for i, char in enumerate(text):
        # 随机颜色（深色）
        color = (
            random.randint(0, 100),
            random.randint(0, 100),
            random.randint(0, 100)
        )
        
        # 计算字符位置
        x = char_width * i + random.randint(5, 15)
        y = random.randint(5, 15)
        
        # 绘制字符
        draw.text((x, y), char, font=font, fill=color)
    
    # 应用模糊滤镜（轻微）
    image = image.filter(ImageFilter.BLUR)
    
    # 转换为字节
    img_bytes = BytesIO()
    image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # 转换为 base64
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    
    return img_base64


def verify_captcha(user_input: str, stored_value: str) -> bool:
    """
    验证验证码（不区分大小写）
    
    Args:
        user_input: 用户输入
        stored_value: 存储的正确值
        
    Returns:
        是否匹配
    """
    if not user_input or not stored_value:
        return False
    
    return user_input.upper().strip() == stored_value.upper().strip()

