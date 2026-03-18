"""Async Celery tasks for sending emails."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config.settings import settings
from src.core.celery.celery_app import celery_app

logger = logging.getLogger("email_task")

FRONTEND_URL = settings.FRONTEND_URL


# ── Shared SMTP helper ────────────────────────────────────────────────────────

def _smtp_send(to_email: str, subject: str, html_body: str, plain_body: str) -> None:
    """Build and deliver a MIME email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.EMAIL_FROM
    msg["To"]      = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body,  "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())


# ── Existing task ──────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10,queue="auth_email")
def send_password_reset_email(self, recipient_email: str, reset_link: str) -> None:
    """Send a password reset email. Retries up to 3 times on failure."""
    logger.info(f"[attempt {self.request.retries + 1}/3] Sending reset email → {recipient_email}")

    try:
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>Password Reset Request</h2>
            <p>We received a request to reset your password.</p>
            <p>Click the button below to choose a new password.
               This link expires in <strong>15 minutes</strong>.</p>
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

        logger.debug(f"Connecting to SMTP {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        _smtp_send(recipient_email, "Reset your password", html_body, plain_body)
        logger.info(f"Reset email successfully sent → {recipient_email}")

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(f"SMTP auth failed — check SMTP_USER/SMTP_PASSWORD | {exc}")
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


# ── New task: staff (support_agent / team_lead) welcome ───────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10,queue="auth_email")
def send_staff_welcome_email(
    self,
    to_email: str,
    name: str,
    role: str,
    temp_password: str,
) -> None:
    """
    Send welcome + temp credentials email to a newly created staff member
    (support_agent or team_lead).
    Fires asynchronously so the POST /admin/staff response is instant.
    """
    logger.info(f"[attempt {self.request.retries + 1}/3] Sending staff welcome → {to_email}")
    try:
        role_label = "Support Agent" if role == "support_agent" else "Team Lead"
        subject    = "Welcome to TicketingGenie — Your Account Details"
        html_body = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:32px;
                    border:1px solid #e2e8f0;border-radius:12px">
          <h2 style="color:#1D4ED8;margin-bottom:4px">Welcome to TicketingGenie</h2>
          <p style="color:#64748B;margin-top:0">Hi <strong>{name}</strong>,</p>
          <p>An account has been created for you as a <strong>{role_label}</strong>.</p>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;
                      padding:20px;margin:20px 0">
            <p style="margin:0 0 8px;font-size:13px;color:#64748B;text-transform:uppercase;
                      letter-spacing:.06em;font-weight:700">Your Credentials</p>
            <p style="margin:4px 0"><strong>Email:</strong> {to_email}</p>
            <p style="margin:4px 0"><strong>Temporary Password:</strong>
              <code style="background:#EFF6FF;color:#1D4ED8;padding:2px 8px;
                           border-radius:4px;font-size:15px">{temp_password}</code>
            </p>
          </div>
          <p>Please log in and <strong>change your password immediately</strong>.</p>
          <a href="{FRONTEND_URL}/login"
             style="display:inline-block;background:#1D4ED8;color:white;padding:12px 28px;
                    border-radius:8px;text-decoration:none;font-weight:600">
            Log In Now
          </a>
          <p style="margin-top:32px;font-size:12px;color:#94A3B8">
            If you did not expect this email, please contact your administrator.
          </p>
        </div>
        """
        plain_body = (
            f"Hi {name},\n\n"
            f"An account has been created for you as a {role_label} on TicketingGenie.\n\n"
            f"Email: {to_email}\n"
            f"Temporary password: {temp_password}\n\n"
            f"Log in at {FRONTEND_URL}/login and change your password immediately.\n\n"
            f"If you did not expect this, contact your administrator."
        )
        _smtp_send(to_email, subject, html_body, plain_body)
        logger.info(f"Staff welcome sent → {to_email}")

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(f"SMTP auth failed: {exc}")
        raise

    except smtplib.SMTPConnectError as exc:
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error(f"Unexpected error on attempt {self.request.retries + 1}: {exc}")
        raise self.retry(exc=exc)


# ── New task: org_admin welcome ────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10,queue="auth_email")
def send_org_admin_welcome_email(
    self,
    to_email: str,
    name: str,
    org_name: str,
    temp_password: str,
) -> None:
    """
    Send welcome + temp credentials email to a newly created org_admin.
    Fires asynchronously so the POST /organisations/ response is instant.
    """
    logger.info(f"[attempt {self.request.retries + 1}/3] Sending org_admin welcome → {to_email}")
    try:
        subject = f"You're the Organisation Admin for {org_name} — TicketingGenie"
        html_body = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:32px;
                    border:1px solid #e2e8f0;border-radius:12px">
          <h2 style="color:#7C3AED">Welcome to TicketingGenie</h2>
          <p>Hi <strong>{name}</strong>,</p>
          <p>You have been set up as the <strong>Organisation Admin</strong> for
             <strong>{org_name}</strong>.</p>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;
                      padding:20px;margin:20px 0">
            <p style="margin:4px 0"><strong>Email:</strong> {to_email}</p>
            <p style="margin:4px 0"><strong>Temporary Password:</strong>
              <code style="background:#F5F3FF;color:#7C3AED;padding:2px 8px;
                           border-radius:4px">{temp_password}</code>
            </p>
          </div>
          <p>You will be prompted to <strong>change your password</strong> on first login.</p>
          <a href="{FRONTEND_URL}/login"
             style="display:inline-block;background:#7C3AED;color:white;padding:12px 28px;
                    border-radius:8px;text-decoration:none;font-weight:600">
            Log In Now
          </a>
          <p style="margin-top:32px;font-size:12px;color:#94A3B8">
            If you did not expect this, contact the system administrator.
          </p>
        </div>
        """
        plain_body = (
            f"Hi {name},\n\n"
            f"You are the Organisation Admin for {org_name} on TicketingGenie.\n\n"
            f"Email: {to_email}\n"
            f"Temporary password: {temp_password}\n\n"
            f"Log in at {FRONTEND_URL}/login and change your password immediately.\n\n"
            f"If you did not expect this, contact the system administrator."
        )
        _smtp_send(to_email, subject, html_body, plain_body)
        logger.info(f"org_admin welcome sent → {to_email}")

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(f"SMTP auth failed: {exc}")
        raise

    except smtplib.SMTPConnectError as exc:
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error(f"Unexpected error on attempt {self.request.retries + 1}: {exc}")
        raise self.retry(exc=exc)


# ── New task: customer welcome ─────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10,queue="auth_email")
def send_customer_welcome_email(
    self,
    to_email: str,
    name: str,
    org_name: str,
    temp_password: str,
) -> None:
    """
    Send welcome + temp credentials email to a newly added customer user.
    """
    logger.info(f"[attempt {self.request.retries + 1}/3] Sending customer welcome → {to_email}")
    try:
        subject = "Your TicketingGenie Support Portal Account Is Ready"
        html_body = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:32px;
                    border:1px solid #e2e8f0;border-radius:12px">
          <h2 style="color:#1D4ED8">Welcome to TicketingGenie</h2>
          <p>Hi <strong>{name}</strong>,</p>
          <p>Your support portal account has been created by <strong>{org_name}</strong>.</p>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;
                      padding:20px;margin:20px 0">
            <p style="margin:4px 0"><strong>Email:</strong> {to_email}</p>
            <p style="margin:4px 0"><strong>Temporary Password:</strong>
              <code style="background:#EFF6FF;color:#1D4ED8;padding:2px 8px;
                           border-radius:4px">{temp_password}</code>
            </p>
          </div>
          <p>You will be prompted to <strong>change your password</strong> on first login.</p>
          <a href="{FRONTEND_URL}/login"
             style="display:inline-block;background:#1D4ED8;color:white;padding:12px 28px;
                    border-radius:8px;text-decoration:none;font-weight:600">
            Log In Now
          </a>
          <p style="margin-top:32px;font-size:12px;color:#94A3B8">
            If you did not expect this, contact your organisation administrator.
          </p>
        </div>
        """
        plain_body = (
            f"Hi {name},\n\n"
            f"Your account on the TicketingGenie portal was created by {org_name}.\n\n"
            f"Email: {to_email}\n"
            f"Temporary password: {temp_password}\n\n"
            f"Log in at {FRONTEND_URL}/login and change your password immediately.\n\n"
            f"Contact your organisation administrator if you did not expect this."
        )
        _smtp_send(to_email, subject, html_body, plain_body)
        logger.info(f"Customer welcome sent → {to_email}")

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(f"SMTP auth failed: {exc}")
        raise

    except smtplib.SMTPConnectError as exc:
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error(f"Unexpected error on attempt {self.request.retries + 1}: {exc}")
        raise self.retry(exc=exc)