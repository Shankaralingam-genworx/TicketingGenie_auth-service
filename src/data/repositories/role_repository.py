"""Repository for role-related database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.role_model import Role


class RoleRepository:
    """Handles all DB operations for roles."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_name(self, name: str) -> Role | None:
        """Fetch a role by its name."""
        result = await self.db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Role]:
        """Fetch all roles."""
        result = await self.db.execute(select(Role))
        return list(result.scalars().all())

    async def create(self, name: str) -> Role:
        """Create a new role."""
        role = Role(name=name)
        self.db.add(role)
        await self.db.flush()
        return role
