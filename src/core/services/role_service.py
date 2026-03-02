"""Business logic for role operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.data.repositories.role_repository import RoleRepository


class RoleService:
    """Handles role-related business logic."""

    def __init__(self, db: AsyncSession):
        self.repo = RoleRepository(db)

    async def seed_roles(self) -> None:
        """Seed the default roles if they don't exist yet."""
        for role_name in RoleName:
            existing = await self.repo.get_by_name(role_name.value)
            if not existing:
                await self.repo.create(role_name.value)

    async def get_role_by_name(self, name: str):
        """Fetch a role by name."""
        return await self.repo.get_by_name(name)

    async def get_all_roles(self):
        """Fetch all roles."""
        return await self.repo.get_all()
