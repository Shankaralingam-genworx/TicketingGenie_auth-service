"""Email service — sends transactional emails via SMTP.

Configure in .env:
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your@email.com
  SMTP_PASSWORD=yourapppassword
  EMAIL_FROM=noreply@ticketinggenie.com
  FRONTEND_URL=https://app.ticketinggenie.com
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config.settings import settings

logger = logging.getLogger("email.service")

FRONTEND_URL = settings.FRONTEND_URL


class EmailService:

    def _send(self, to_email: str, subject: str, html: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.EMAIL_FROM
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
            logger.info(f"Email sent → {to_email} | {subject}")
        except Exception as e:
            # Log but don't crash the request — account is still created
            logger.error(f"Failed to send email to {to_email}: {e}")

    # ── Existing: staff welcome (support_agent / team_lead) ───────────────────

    async def send_welcome(
        self,
        to_email: str,
        name: str,
        role: str,
        temp_password: str,
    ) -> None:
        role_label = "Support Agent" if role == "support_agent" else "Team Lead"
        subject    = "Welcome to TicketingGenie — Your Account Details"
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:32px;border:1px solid #e2e8f0;border-radius:12px">
          <h2 style="color:#1D4ED8;margin-bottom:4px">Welcome to TicketingGenie</h2>
          <p style="color:#64748B;margin-top:0">Hi <strong>{name}</strong>,</p>
          <p>An account has been created for you as a <strong>{role_label}</strong>.</p>

          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:20px;margin:20px 0">
            <p style="margin:0 0 8px;font-size:13px;color:#64748B;text-transform:uppercase;letter-spacing:.06em;font-weight:700">Your Credentials</p>
            <p style="margin:4px 0"><strong>Email:</strong> {to_email}</p>
            <p style="margin:4px 0"><strong>Temporary Password:</strong>
              <code style="background:#EFF6FF;color:#1D4ED8;padding:2px 8px;border-radius:4px;font-size:15px">{temp_password}</code>
            </p>
          </div>

          <p>Please log in and <strong>change your password immediately</strong>.</p>
          <a href="{FRONTEND_URL}/login"
             style="display:inline-block;background:#1D4ED8;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600">
            Log In Now
          </a>

          <p style="margin-top:32px;font-size:12px;color:#94A3B8">
            If you did not expect this email, please contact your administrator.
          </p>
        </div>
        """
        self._send(to_email, subject, html)

    # ── New: org_admin welcome ─────────────────────────────────────────────────

    async def send_org_admin_welcome(
        self,
        to_email: str,
        name: str,
        org_name: str,
        temp_password: str,
    ) -> None:
        """Sent when the system admin creates a new organisation + org_admin."""
        subject = f"You're the Organisation Admin for {org_name} — TicketingGenie"
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:32px;border:1px solid #e2e8f0;border-radius:12px">
          <h2 style="color:#7C3AED;margin-bottom:4px">Welcome to TicketingGenie</h2>
          <p style="color:#64748B;margin-top:0">Hi <strong>{name}</strong>,</p>
          <p>You have been set up as the <strong>Organisation Admin</strong> for
             <strong>{org_name}</strong> on the TicketingGenie support portal.</p>

          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:20px;margin:20px 0">
            <p style="margin:0 0 8px;font-size:13px;color:#64748B;text-transform:uppercase;letter-spacing:.06em;font-weight:700">Your Credentials</p>
            <p style="margin:4px 0"><strong>Email:</strong> {to_email}</p>
            <p style="margin:4px 0"><strong>Temporary Password:</strong>
              <code style="background:#F5F3FF;color:#7C3AED;padding:2px 8px;border-radius:4px;font-size:15px">{temp_password}</code>
            </p>
          </div>

          <p>You will be asked to <strong>change your password</strong> when you first log in.</p>
          <p>Once logged in you can:</p>
          <ul>
            <li>Add customer users from your organisation</li>
            <li>View all support tickets raised by your customers</li>
          </ul>

          <a href="{FRONTEND_URL}/login"
             style="display:inline-block;background:#7C3AED;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600">
            Log In Now
          </a>

          <p style="margin-top:32px;font-size:12px;color:#94A3B8">
            If you did not expect this email, please contact the system administrator.
          </p>
        </div>
        """
        self._send(to_email, subject, html)

    # ── New: customer welcome ──────────────────────────────────────────────────

    async def send_customer_welcome(
        self,
        to_email: str,
        name: str,
        org_name: str,
        temp_password: str,
    ) -> None:
        """Sent when an org_admin adds a new customer user to their organisation."""
        subject = "Your TicketingGenie Support Portal Account Is Ready"
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:32px;border:1px solid #e2e8f0;border-radius:12px">
          <h2 style="color:#1D4ED8;margin-bottom:4px">Welcome to TicketingGenie</h2>
          <p style="color:#64748B;margin-top:0">Hi <strong>{name}</strong>,</p>
          <p>Your support portal account has been created by
             <strong>{org_name}</strong>.</p>

          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:20px;margin:20px 0">
            <p style="margin:0 0 8px;font-size:13px;color:#64748B;text-transform:uppercase;letter-spacing:.06em;font-weight:700">Your Credentials</p>
            <p style="margin:4px 0"><strong>Email:</strong> {to_email}</p>
            <p style="margin:4px 0"><strong>Temporary Password:</strong>
              <code style="background:#EFF6FF;color:#1D4ED8;padding:2px 8px;border-radius:4px;font-size:15px">{temp_password}</code>
            </p>
          </div>

          <p>You will be asked to <strong>change your password</strong> when you first log in.</p>
          <p>Once logged in you can raise support tickets and track their progress.</p>

          <a href="{FRONTEND_URL}/login"
             style="display:inline-block;background:#1D4ED8;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600">
            Log In Now
          </a>

          <p style="margin-top:32px;font-size:12px;color:#94A3B8">
            If you did not expect this email, please contact your organisation administrator.
          </p>
        </div>
        """
        self._send(to_email, subject, html)