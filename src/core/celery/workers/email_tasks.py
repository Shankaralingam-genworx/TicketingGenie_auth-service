"""Async Celery tasks for sending emails."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config.settings import settings
from src.core.celery.celery_app import celery_app

logger = logging.getLogger("email_task")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_password_reset_email(self, recipient_email: str, reset_link: str) -> None:
    """Send a password reset email. Retries up to 3 times on failure."""
    logger.info(f"[attempt {self.request.retries + 1}/3] Sending reset email → {recipient_email}")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your password"
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = recipient_email

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>Password Reset Request</h2>
            <p>We received a request to reset your password.</p>
            <p>Click the button below to choose a new password. This link expires in <strong>15 minutes</strong>.</p>
            <p style="margin: 24px 0;">
              <a href="{reset_link}"
                 style="background:#4F46E5;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;">
                Reset Password
              </a>
            </p>
            <p>If you didn't request this, you can safely ignore this email.</p>
            <hr/>
            <small style="color:#999;">This link will expire in 15 minutes.</small>
          </body>
        </html>
        """

        plain_body = (
            f"Reset your password using the link below (expires in 15 minutes):\n\n"
            f"{reset_link}\n\n"
            f"If you didn't request this, ignore this email."
        )

        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        logger.debug(f"Connecting to SMTP {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            logger.debug("SMTP ehlo OK")
            server.starttls()
            logger.debug("SMTP starttls OK")
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            logger.debug(f"SMTP login OK as {settings.SMTP_USER}")
            server.sendmail(settings.EMAIL_FROM, recipient_email, msg.as_string())

        logger.info(f"Reset email successfully sent → {recipient_email}")

    except smtplib.SMTPAuthenticationError as exc:
        # Bad credentials — retrying won't help, fail immediately
        logger.error(f"SMTP auth failed — check SMTP_USER/SMTP_PASSWORD in .env | {exc}")
        raise

    except smtplib.SMTPConnectError as exc:
        logger.error(f"SMTP connection failed to {settings.SMTP_HOST}:{settings.SMTP_PORT} | {exc}")
        raise self.retry(exc=exc)

    except smtplib.SMTPException as exc:
        logger.error(f"SMTP error on attempt {self.request.retries + 1}: {exc}")
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error(f"Unexpected error on attempt {self.request.retries + 1}: {exc}")
        raise self.retry(exc=exc)