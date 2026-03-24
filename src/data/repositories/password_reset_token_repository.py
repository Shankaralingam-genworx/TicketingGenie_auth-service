"""Repository for password reset token database operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.password_reset_token_model import PasswordResetToken


class PasswordResetTokenRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, user_id: int, token: str, expires_at: datetime
    ) -> PasswordResetToken:
        record = PasswordResetToken(
            user_id=user_id, token=token, expires_at=expires_at
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_by_token(self, token: str) -> PasswordResetToken | None:
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, record: PasswordResetToken) -> None:
        record.used = True
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: int) -> None:
        """
        Mark all unused/unexpired reset tokens for this user as used.

        Called before creating a new reset token so that only the latest
        link is valid — prevents accumulation of multiple live reset tokens
        per user which could be exploited if an older email is intercepted.
        """
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used.is_(False),
            )
        )
        for record in result.scalars().all():
            record.used = True
        await self.db.flush()