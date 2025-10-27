"""
邮件发送服务
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


class EmailService:
    """邮件发送服务"""
    
    @staticmethod
    async def send_verification_code(to_email: str, code: str) -> bool:
        """
        发送验证码邮件
        
        Args:
            to_email: 收件人邮箱
            code: 验证码
            
        Returns:
            是否发送成功
        """
        try:
            # 创建邮件
            message = MIMEMultipart()
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            message["Subject"] = "验证码 - RAG API"
            
            # 邮件正文（HTML）
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #333;">邮箱验证码</h2>
                        <p>您好，</p>
                        <p>您的验证码是：</p>
                        <div style="background-color: #f5f5f5; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; margin: 20px 0;">
                            {code}
                        </div>
                        <p style="color: #666;">验证码有效期为 5 分钟，请勿泄露给他人。</p>
                        <p style="color: #999; font-size: 12px; margin-top: 30px;">如果这不是您的操作，请忽略此邮件。</p>
                    </div>
                </body>
            </html>
            """
            
            message.attach(MIMEText(html, "html"))
            
            # 发送邮件
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
            
            return True
            
        except Exception as e:
            print(f"发送邮件失败: {e}")
            return False


# 全局实例
email_service = EmailService()

