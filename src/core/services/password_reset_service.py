"""Business logic for forgot password and reset password flows."""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.core.exceptions.auth_exceptions import InvalidTokenException, UserNotFoundException
from src.data.repositories.password_reset_token_repository import PasswordResetTokenRepository
from src.data.repositories.refresh_token_repository import RefreshTokenRepository
from src.data.repositories.user_repository import UserRepository
from src.core.celery.workers.email_tasks import send_password_reset_email
from src.utils.auth_utils import get_current_time


class PasswordResetService:

    def __init__(self, db: AsyncSession):
        self.user_repo        = UserRepository(db)
        self.reset_token_repo = PasswordResetTokenRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)

    async def forgot_password(self, email: str) -> None:
        """
        Always returns without error to prevent email enumeration.
        Sends a reset link only when the email exists in the system.

        Invalidates any previous unused reset tokens for this user so that
        only the latest link is valid.
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            return  # silent — do not reveal whether the email exists

        # Revoke all outstanding unused tokens before creating a new one
        # so that old links cannot be used after a new request is made.
        await self.reset_token_repo.revoke_all_for_user(user.id)

        token      = secrets.token_urlsafe(32)
        expires_at = get_current_time() + timedelta(
            minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
        )
        await self.reset_token_repo.create(user.id, token, expires_at)

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        # Fire-and-forget via Celery — non-blocking
        send_password_reset_email.delay(user.email, reset_link)

    async def reset_password(self, token: str, new_password: str) -> None:
        """
        Validates the reset token, updates the password (via the repo so that
        must_change_password is cleared), marks the token used, and revokes
        all active refresh tokens.
        """
        record = await self.reset_token_repo.get_by_token(token)

        if not record:
            raise InvalidTokenException("Invalid or expired reset token")
        if record.used:
            raise InvalidTokenException("Reset token has already been used")
        if record.expires_at < datetime.now(timezone.utc):
            raise InvalidTokenException("Reset token has expired")

        # Verify the user still exists
        user = await self.user_repo.get_by_id(record.user_id)
        if not user:
            raise UserNotFoundException("User account no longer exists.")

        # Use update_password() — this also clears must_change_password=False,
        # which is critical so that a reset does not leave the user stuck in the
        # forced-change-password loop on next login.
        from src.utils.password_utils import hash_password
        await self.user_repo.update_password(user.id, hash_password(new_password))

        # One-time use — mark before committing
        await self.reset_token_repo.mark_used(record)

        # Invalidate all active sessions — force re-login with new password
        await self.refresh_token_repo.revoke_all_for_user(record.user_id)