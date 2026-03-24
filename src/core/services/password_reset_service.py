"""Forgot-password and reset-password flows."""

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
from src.observability.logging.logger import get_logger

logger = get_logger(__name__).bind(service="auth-service")


class PasswordResetService:

    def __init__(self, db: AsyncSession):
        self.user_repo          = UserRepository(db)
        self.reset_token_repo   = PasswordResetTokenRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)

    async def forgot_password(self, email: str) -> None:
        """Silent on unknown email — prevents email enumeration."""
        logger.info("forgot_password_started")

        user = await self.user_repo.get_by_email(email)
        if not user:
            # Log at debug only — don't expose whether the email exists
            logger.debug("forgot_password_email_not_found")
            return

        # Invalidate old tokens so only the latest link works
        await self.reset_token_repo.revoke_all_for_user(user.id)

        token      = secrets.token_urlsafe(32)
        expires_at = get_current_time() + timedelta(
            minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
        )
        await self.reset_token_repo.create(user.id, token, expires_at)

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        logger.info("forgot_password_sending_email", user_id=user.id)

        send_password_reset_email.delay(user.email, reset_link)

        logger.info("forgot_password_email_sent", user_id=user.id)

    async def reset_password(self, token: str, new_password: str) -> None:
        """Validate token, update password, revoke all active sessions."""
        logger.info("reset_password_started")

        record = await self.reset_token_repo.get_by_token(token)

        if not record:
            logger.warning("reset_password_token_invalid")
            raise InvalidTokenException("Invalid or expired reset token")

        if record.used:
            logger.warning("reset_password_token_already_used")
            raise InvalidTokenException("Reset token has already been used")

        if record.expires_at < datetime.now(timezone.utc):
            logger.warning("reset_password_token_expired")
            raise InvalidTokenException("Reset token has expired")

        user = await self.user_repo.get_by_id(record.user_id)
        if not user:
            logger.warning("reset_password_user_not_found", user_id=record.user_id)
            raise UserNotFoundException("User account no longer exists.")

        from src.utils.password_utils import hash_password
        await self.user_repo.update_password(user.id, hash_password(new_password))

        await self.reset_token_repo.mark_used(record)

        # Force re-login — all existing sessions are now invalid
        await self.refresh_token_repo.revoke_all_for_user(record.user_id)

        logger.info("reset_password_success", user_id=user.id)