import logging 
import smtplib 
from email.message import EmailMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

class MailerService:
    def _send_email(self, msg: EmailMessage) -> None:
        if not all([
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
        ]):
            logger.warning("SMTP configuration is incomplete, skipping email")
            return 
            
        try:
            with smtplib.SMTP_SSL(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT
            ) as server:
                server.login(user=settings.SMTP_USER, password=settings.SMTP_PASSWORD)
                server.send_message(msg)
                logger.info(f"Email sent to {msg['To']}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
    
    async def send_2fa_code(self, recipient_email: str, user_name: str, code: str) -> None:
        """Send 2FA verification code via email"""
        msg = EmailMessage()
        msg['Subject'] = "Two-Factor Authentication Code"
        msg['From'] = f"{settings.SMTP_FROM} <{settings.SMTP_USER}>"
        msg['To'] = recipient_email
        
        msg.set_content(f"""
Hello {user_name},

Your two-factor authentication code is: {code}

This code will expire in 5 minutes. Please use it to complete your login.

If you did not request this code, please ignore this email and ensure your account is secure.

Best regards,
{settings.APP_NAME} Team
        """.strip())
        
        self._send_email(msg)
    
    async def send_email_verification(self, recipient_email: str, user_name: str, token: str) -> None:
        """Send email verification link"""
        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        msg = EmailMessage()
        msg['Subject'] = f"Verify Your Email Address - {settings.APP_NAME}"
        msg['From'] = f"{settings.SMTP_FROM} <{settings.SMTP_USER}>"
        msg['To'] = recipient_email
        
        msg.set_content(f"""
Hello {user_name},

Welcome to {settings.APP_NAME}! Please verify your email address by clicking the link below:

{verification_link}

This verification link will expire in 24 hours.

If you did not create an account with us, please ignore this email.

Best regards,
{settings.APP_NAME} Team
        """.strip())
        
        self._send_email(msg)
    
    async def send_welcome_email(self, recipient_email: str, user_name: str) -> None:
        """Send welcome email after successful verification"""
        msg = EmailMessage()
        msg['Subject'] = f"Welcome to {settings.APP_NAME}!"
        msg['From'] = f"{settings.SMTP_FROM} <{settings.SMTP_USER}>"
        msg['To'] = recipient_email
        
        msg.set_content(f"""
Hello {user_name},

Welcome to {settings.APP_NAME}! Your email has been successfully verified and your account is now active.

You can now:
- Access your dashboard
- Manage your organization settings
- Enable two-factor authentication for additional security

If you have any questions, please don't hesitate to contact our support team.

Best regards,
{settings.APP_NAME} Team
        """.strip())
        
        self._send_email(msg)
    
    async def send_password_changed_notification(self, recipient_email: str, user_name: str) -> None:
        """Send notification when password is changed"""
        msg = EmailMessage()
        msg['Subject'] = "Password Changed Successfully"
        msg['From'] = f"{settings.SMTP_FROM} <{settings.SMTP_USER}>"
        msg['To'] = recipient_email
        
        msg.set_content(f"""
Hello {user_name},

Your password has been successfully changed. If you made this change, you can safely ignore this email.

If you did not change your password, please contact our support team immediately and consider:
- Changing your password again
- Enabling two-factor authentication
- Reviewing your account activity

Best regards,
{settings.APP_NAME} Team
        """.strip())
        
        self._send_email(msg)
    
    async def send_2fa_enabled_notification(self, recipient_email: str, user_name: str) -> None:
        """Send notification when 2FA is enabled"""
        msg = EmailMessage()
        msg['Subject'] = "Two-Factor Authentication Enabled"
        msg['From'] = f"{settings.SMTP_FROM} <{settings.SMTP_USER}>"
        msg['To'] = recipient_email
        
        msg.set_content(f"""
Hello {user_name},

Two-factor authentication has been successfully enabled on your account. This adds an extra layer of security to protect your account.

From now on, you'll need to enter a verification code sent to this email address when logging in.

If you did not enable this feature, please contact our support team immediately.

Best regards,
{settings.APP_NAME} Team
        """.strip())
        
        self._send_email(msg)

mailer_service = MailerService()