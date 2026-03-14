"""Business logic for forgot password and reset password flows."""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.core.exceptions.auth_exceptions import InvalidTokenException
from src.core.security import hash_password
from src.data.repositories.password_reset_token_repository import PasswordResetTokenRepository
from src.data.repositories.refresh_token_repository import RefreshTokenRepository
from src.data.repositories.user_repository import UserRepository
from src.core.celery.workers.email_tasks import send_password_reset_email
from src.utils.auth_utils import get_current_time




class PasswordResetService:

    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.reset_token_repo = PasswordResetTokenRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)

    async def forgot_password(self, email: str) -> None:
        """
        Always returns without error to prevent email enumeration.
        Sends a reset link only when the email exists in the system.
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            return  # silent — do not reveal whether email exists

        token = secrets.token_urlsafe(32)
        expires_at = get_current_time() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

        await self.reset_token_repo.create(user.id, token, expires_at)

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        # Fire-and-forget via Celery — non-blocking
        send_password_reset_email.delay(user.email, reset_link)

    async def reset_password(self, token: str, new_password: str) -> None:
        """
        Validates the reset token, updates the password,
        marks the token used, and revokes all active refresh tokens.
        """
        record = await self.reset_token_repo.get_by_token(token)

        if not record:
            raise InvalidTokenException("Invalid or expired reset token")
        if record.used:
            raise InvalidTokenException("Reset token has already been used")
        if record.expires_at < datetime.now(timezone.utc):
            raise InvalidTokenException("Reset token has expired")

        # Update password
        user = await self.user_repo.get_by_id(record.user_id)
        user.password_hash = hash_password(new_password)

        # One-time use
        await self.reset_token_repo.mark_used(record)

        # Invalidate all active sessions
        await self.refresh_token_repo.revoke_all_for_user(record.user_id)