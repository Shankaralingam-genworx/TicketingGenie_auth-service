"""
Email service — sends transactional emails via SMTP.

Configure in .env:
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your@email.com
  SMTP_PASSWORD=yourapppassword
  EMAIL_FROM=noreply@ticketinggenie.com
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config.settings import settings   # adjust import to your settings module

logger = logging.getLogger("email.service")

FRONTEND_URL =  settings.FRONTEND_URL


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
            # Log but don't crash the request — staff is still created
            logger.error(f"Failed to send email to {to_email}: {e}")

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