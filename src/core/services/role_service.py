"""Business logic for role operations.

Roles are seeded from RoleName enum (the four built-in roles) plus any
additional roles listed explicitly in main.py (e.g. org_admin).
Adding a role to the DB via the /roles endpoint also makes it available
at runtime — no code change needed.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.data.models.postgres.role_model import Role
from src.data.repositories.role_repository import RoleRepository


class RoleService:
    """Handles role-related business logic."""

    def __init__(self, db: AsyncSession):
        self.repo = RoleRepository(db)

    async def seed_roles(self) -> None:
        """Seed the four built-in roles from RoleName if they don't exist yet."""
        for role_name in RoleName:
            existing = await self.repo.get_by_name(role_name.value)
            if not existing:
                await self.repo.create(role_name.value)

    async def get_role_by_name(self, name: str) -> Role | None:
        return await self.repo.get_by_name(name)

    async def get_role_by_id(self, role_id: int) -> Role | None:
        return await self.repo.get_by_id(role_id)

    async def get_all_roles(self) -> list[Role]:
        return await self.repo.get_all()

    async def create_role(self, name: str) -> Role:
        return await self.repo.create(name)

    async def update_role(self, role_id: int, name: str) -> Role | None:
        return await self.repo.update(role_id, name)

    async def delete_role(self, role_id: int) -> None:
        await self.repo.delete(role_id)

    async def is_role_in_use(self, role_id: int) -> bool:
        count = await self.repo.count_users_with_role(role_id)
        return count > 0