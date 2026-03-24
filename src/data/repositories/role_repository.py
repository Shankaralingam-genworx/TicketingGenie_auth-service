"""Repository for role-related database operations."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.role_model import Role
from src.data.models.postgres.user_model import User


class RoleRepository:
    """Handles all DB operations for roles."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_name(self, name: str) -> Role | None:
        """Fetch a role by its name."""
        result = await self.db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_by_id(self, role_id: int) -> Role | None:
        """Fetch a role by its ID."""
        result = await self.db.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Role]:
        """Fetch all roles ordered by id."""
        result = await self.db.execute(select(Role).order_by(Role.id))
        return list(result.scalars().all())

    async def create(self, name: str) -> Role:
        """Create a new role."""
        role = Role(name=name)
        self.db.add(role)
        await self.db.flush()
        return role

    async def update(self, role_id: int, name: str) -> Role | None:
        """Rename a role."""
        role = await self.get_by_id(role_id)
        if not role:
            return None
        role.name = name
        await self.db.flush()
        return role

    async def delete(self, role_id: int) -> None:
        """Hard-delete a role by ID."""
        role = await self.get_by_id(role_id)
        if role:
            await self.db.delete(role)
            await self.db.flush()

    async def count_users_with_role(self, role_id: int) -> int:
        """Return how many users are assigned this role."""
        result = await self.db.execute(
            select(func.count()).where(User.role_id == role_id)
        )
        return result.scalar_one()