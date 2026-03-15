"""Repository for password reset token database operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.password_reset_token_model import PasswordResetToken


class PasswordResetTokenRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, token: str, expires_at: datetime) -> PasswordResetToken:
        record = PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
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