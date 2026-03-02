"""Repository for user-related database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.postgres.user_model import User


class UserRepository:
    """Handles all DB operations for users."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        """Fetch a user by ID, with role and customer loaded."""
        result = await self.db.execute(select(User)
        .options(
            selectinload(User.role),
            selectinload(User.customer),   # ← ADD THIS
        )
        .where(User.id == user_id)
    )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email, with role loaded."""
        result = await self.db.execute(
            select(User).options(selectinload(User.role)).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[User]:
        """Fetch all users with their roles."""
        result = await self.db.execute(
            select(User).options(selectinload(User.role)).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, name: str, email: str, password_hash: str, role_id: int) -> User:
        """Create a new user."""
        user = User(name=name, email=email, password_hash=password_hash, role_id=role_id)
        self.db.add(user)
        await self.db.flush()
        # Reload with role
        return await self.get_by_id(user.id)
