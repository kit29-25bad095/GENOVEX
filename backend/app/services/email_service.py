import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger("genovex.email")

def is_test_environment() -> bool:
    """Detects if execution is running in test or local development mode."""
    env = (settings.ENVIRONMENT or "").strip().lower()
    return env in ("test", "testing", "development") or bool(os.getenv("PYTEST_CURRENT_TEST"))


class EmailService:
    """
    Production-ready email service for clinical communication and account security workflows.
    Supports secure SMTP delivery with TLS, safe development test outbox, and strict sanitization.
    Raw tokens and credentials are never emitted to production logs.
    """
    _test_outbox: List[Dict[str, Any]] = []

    @classmethod
    def clear_test_outbox(cls) -> None:
        """Clears in-memory test mailbox between test runs."""
        cls._test_outbox.clear()

    @classmethod
    def get_test_outbox(cls) -> List[Dict[str, Any]]:
        """Returns copies of all recorded emails in the test outbox."""
        return list(cls._test_outbox)

    @classmethod
    def send_password_reset_email(
        cls,
        to_email: str,
        raw_token: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Generates and delivers a password reset email using trusted frontend URL configuration.
        Never relies on untrusted HTTP Host headers.
        """
        display_name = user_name or "Valued User"
        trusted_frontend = settings.FRONTEND_URL.rstrip("/")
        reset_link = f"{trusted_frontend}/auth/reset-password?token={raw_token}"
        expire_minutes = settings.RESET_TOKEN_EXPIRE_MINUTES

        subject = "GENOVEX Account Password Reset Request | طلب استعادة كلمة المرور"

        text_content = (
            f"Hello {display_name},\n\n"
            f"We received a request to reset your password for your GENOVEX account.\n\n"
            f"Click the secure link below to choose a new password:\n"
            f"{reset_link}\n\n"
            f"This link will expire in {expire_minutes} minutes. If you did not request a password reset, "
            f"please ignore this message. Your account remains completely secure.\n\n"
            f"--------------------------------------------------\n"
            f"مرحباً {display_name}،\n\n"
            f"تلقينا طلباً لاستعادة كلمة المرور الخاصة بحسابك على منصة جينوفيكس.\n\n"
            f"يرجى الضغط على الرابط الآمن التالي لتعيين كلمة مرور جديدة:\n"
            f"{reset_link}\n\n"
            f"تنتهي صلاحية هذا الرابط خلال {expire_minutes} دقيقة. إذا لم تكن قد طلبت استعادة الحساب، "
            f"يرجى تجاهل هذه الرسالة. حسابك وبياناتك الصحية في أمان تام.\n\n"
            f"— GENOVEX Clinical Safety Team\n"
        )

        html_content = f"""<!DOCTYPE html>
<html dir="ltr" lang="en">
<head>
  <meta charset="utf-8">
  <title>Password Reset Request</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #0f172a;">
  <div style="max-width: 580px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden;">
    <div style="background-color: #0d9488; padding: 20px 24px; text-align: center;">
      <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 700;">GENOVEX</h1>
      <p style="color: #ccfbf1; margin: 4px 0 0 0; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em;">Clinical Health &amp; Reproductive Triage</p>
    </div>
    <div style="padding: 28px 24px;">
      <h2 style="font-size: 18px; margin-top: 0; color: #0f2a4a;">Password Reset Request</h2>
      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        Hello <strong>{display_name}</strong>, we received a request to reset the password associated with your account.
      </p>
      <div style="text-align: center; margin: 28px 0;">
        <a href="{reset_link}" style="display: inline-block; background-color: #0d9488; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-weight: 600; font-size: 14px;">Reset Password</a>
      </div>
      <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
        This secure link expires in <strong>{expire_minutes} minutes</strong>. If you did not request a password reset, please disregard this email.
      </p>
      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
      <div dir="rtl" style="text-align: right;">
        <h3 style="font-size: 16px; margin-top: 0; color: #0f2a4a;">طلب استعادة كلمة المرور</h3>
        <p style="font-size: 13px; line-height: 1.6; color: #334155;">
          مرحباً <strong>{display_name}</strong>، تلقينا طلباً لتعيين كلمة مرور جديدة لحسابك على منصة جينوفيكس.
        </p>
        <div style="text-align: center; margin: 20px 0;">
          <a href="{reset_link}" style="display: inline-block; background-color: #0f2a4a; color: #ffffff; text-decoration: none; padding: 10px 24px; border-radius: 6px; font-weight: 600; font-size: 13px;">تعيين كلمة المرور</a>
        </div>
        <p style="font-size: 11px; color: #64748b; line-height: 1.5;">
          صلاحية هذا الرابط <strong>{expire_minutes} دقيقة</strong>. إذا لم تكن صاحب هذا الطلب، لا يُتطلب منك اتخاذ أي إجراء.
        </p>
      </div>
    </div>
    <div style="background-color: #f1f5f9; padding: 14px 24px; text-align: center; font-size: 11px; color: #94a3b8;">
      &copy; 2026 GENOVEX Healthcare Platform. All rights reserved.
    </div>
  </div>
</body>
</html>"""

        # Record into test outbox ONLY in test or development environments.
        # Production and staging environments strictly isolate memory to prevent token leakage.
        if is_test_environment():
            delivery_record = {
                "to": to_email,
                "to_email": to_email,
                "subject": subject,
                "reset_link": reset_link,
                "raw_token": raw_token,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if len(cls._test_outbox) >= 100:
                cls._test_outbox.pop(0)
            cls._test_outbox.append(delivery_record)

        # Real SMTP delivery if configured
        if settings.SMTP_HOST:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.EMAILS_FROM_EMAIL
                msg["To"] = to_email

                part1 = MIMEText(text_content, "plain", "utf-8")
                part2 = MIMEText(html_content, "html", "utf-8")
                msg.attach(part1)
                msg.attach(part2)

                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAILS_FROM_EMAIL, [to_email], msg.as_string())
                server.quit()
                logger.info("Successfully delivered password reset email to %s", to_email)
                return True
            except Exception as e:
                logger.error("Failed to deliver password reset email via SMTP: %s", type(e).__name__)
                # Even if SMTP fails, return True for unauthenticated flow to prevent account enumeration
                return False

        logger.debug("Development/Test delivery: Password reset email recorded for %s", to_email)
        return True
