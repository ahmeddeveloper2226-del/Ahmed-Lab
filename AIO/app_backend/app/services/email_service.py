import logging

import aiosmtplib
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger("wasla.email")


class EmailSendError(Exception):
    """Raised when the underlying email provider fails to send. Routers
    catch this and turn it into a proper 502, never letting it crash raw."""
    pass


async def send_verification_email(to_email: str, code: str) -> None:
    """
    Sends a real verification email via SMTP.

    Configure via .env:
        SMTP_HOST=smtp.gmail.com
        SMTP_PORT=587
        SMTP_USERNAME=your@gmail.com
        SMTP_PASSWORD=<Gmail App Password — 16 characters, generated at
                       myaccount.google.com/apppasswords, NOT your real
                       Gmail password. Real Gmail passwords are rejected by
                       Google for SMTP; only App Passwords work, and only
                       once 2-Step Verification is enabled on the account.>
        SENDER_EMAIL=your@gmail.com
        SENDER_NAME=Wasla

    Any real SMTP provider works here, not just Gmail — same host/port/
    username/password shape applies whether it's Gmail, a custom domain's
    mail server, Zoho, Outlook, etc.
    """
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        logger.error(
            "SMTP is not configured (smtp_host/smtp_username/smtp_password missing "
            "from .env) — cannot send a real email."
        )
        raise EmailSendError("Email provider not configured")

    message = EmailMessage()
    message["From"] = f"{settings.sender_name} <{settings.sender_email or settings.smtp_username}>"
    message["To"] = to_email
    message["Subject"] = "Your Wasla verification code"
    message.set_content(
        f"Your Wasla verification code is: {code}\n\n"
        f"This code expires in 10 minutes. If you didn't request this, you can ignore this email."
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info(f"Verification email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {to_email}: {e}")
        raise EmailSendError(str(e))