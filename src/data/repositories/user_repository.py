"""Repository for user-related database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.postgres.user_model import User
from src.data.models.postgres.team_model import Team
from src.data.models.postgres.customer_model import Customer
from src.data.models.postgres.team_member_model import TeamMember


class UserRepository:
    """Handles all DB operations for users."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        """Fetch a user by ID, with role and customer loaded."""
        result = await self.db.execute(select(User)
        .options(
            selectinload(User.role),
            selectinload(User.customer),   
        )
        .where(User.id == user_id)
    )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email with related data."""
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.role),
                selectinload(User.customer),
                selectinload(User.led_teams)
            )
            .where(User.email == email)
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
    
    
        """
    Add this method to your existing UserRepository class.
    The rest of the file stays unchanged.
    """

    async def get_by_roles(self, role_names: list[str]):
        """Fetch all users whose role.name is in the given list."""
        from sqlalchemy.orm import selectinload
        from src.data.models.postgres.role_model import Role

        result = await self.db.execute(
            select(User)
            .join(User.role)
            .where(Role.name.in_(role_names))
            .options(
                selectinload(User.role),
                selectinload(User.team_memberships).selectinload(TeamMember.team),
            )
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())
