"""Repository for refresh token database operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.refresh_token_model import RefreshToken


class RefreshTokenRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.jti == jti)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, jti: str, expires_at: datetime) -> RefreshToken:
        rt = RefreshToken(user_id=user_id, jti=jti, expires_at=expires_at)
        self.db.add(rt)
        await self.db.flush()
        return rt

    async def revoke_by_jti(self, jti: str) -> bool:
        rt = await self.get_by_jti(jti)
        if not rt:
            return False
        rt.revoked = True
        await self.db.flush()
        return True

    async def revoke_all_for_user(self, user_id: int) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,  # noqa: E712
            )
        )
        for t in result.scalars().all():
            t.revoked = True
        await self.db.flush()