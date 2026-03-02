"""Repository for refresh token database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.refresh_token_model import RefreshToken
from datetime import datetime


class RefreshTokenRepository:
    """Handles all DB operations for refresh tokens."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Find a refresh token record by the token string."""
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: str, token: str, expires_at: datetime) -> RefreshToken:
        """Store a new refresh token."""
        rt = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        self.db.add(rt)
        await self.db.flush()
        return rt

    async def revoke(self, token: str) -> bool:
        """Mark a refresh token as revoked. Returns True if found and revoked."""
        rt = await self.get_by_token(token)
        if not rt:
            return False
        rt.revoked = True
        await self.db.flush()
        return True

    async def revoke_all_for_user(self, user_id: str) -> None:
        """Revoke all active refresh tokens for a user (e.g. on password change)."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked == False  # noqa: E712
            )
        )
        tokens = result.scalars().all()
        for t in tokens:
            t.revoked = True
        await self.db.flush()
