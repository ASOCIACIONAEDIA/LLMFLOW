import logging 
import smtplib 
from email.message import EmailMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

class MailerService:
    def _send_email(self, msg: EmailMessage) -> None:
        if not all(
            [
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                settings.SMTP_USER,
                settings.SMTP_PASSWORD,
            ]
        ):
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
    
    async def send_2fa_code(self, recipient_email: str, user_name: str, token: str) -> None:
        verfication_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        msg = EmailMessage()
        msg['Subject'] = "2FA Verification Code"
        msg['From'] = f"{settings.SMTP_FROM} <{settings.SMTP_USER}>"
        msg['To'] = recipient_email
        msg.set_content(
            f"""
            Hello {user_name},
            Your 2FA verification code is: {token}
            Please use this code to verify your account.
            You can also use the following link to verify your account:
            {verfication_link}
            If you did not request this verification, please ignore this email.
            """
        )
        self._send_email(msg)

mailer_service = MailerService()