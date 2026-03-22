from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.data.models.postgres.role_model import Role
from src.data.repositories.role_repository import RoleRepository
from src.observability.logging.logger import get_logger

logger = get_logger(__name__).bind(service="auth-service")



class RoleService:

    def __init__(self, db: AsyncSession):
        self.repo = RoleRepository(db)

    async def seed_roles(self) -> None:
        """Seed built-in roles on startup if they don't exist yet."""
        logger.info("seed_roles_started")
        seeded = []
        for role_name in RoleName:
            if not await self.repo.get_by_name(role_name.value):
                await self.repo.create(role_name.value)
                seeded.append(role_name.value)
        logger.info("seed_roles_success", seeded=seeded)

    async def get_role_by_name(self, name: str) -> Role | None:
        return await self.repo.get_by_name(name)

    async def get_role_by_id(self, role_id: int) -> Role | None:
        return await self.repo.get_by_id(role_id)

    async def get_all_roles(self) -> list[Role]:
        return await self.repo.get_all()

    async def create_role(self, name: str) -> Role:
        logger.info("create_role_started", role_name=name)
        role = await self.repo.create(name)
        logger.info("create_role_success", role_id=role.id, role_name=name)
        return role

    async def update_role(self, role_id: int, name: str) -> Role | None:
        logger.info("update_role_started", role_id=role_id, new_name=name)
        role = await self.repo.update(role_id, name)
        if role:
            logger.info("update_role_success", role_id=role_id)
        else:
            logger.warning("update_role_not_found", role_id=role_id)
        return role

    async def delete_role(self, role_id: int) -> None:
        logger.info("delete_role_started", role_id=role_id)
        await self.repo.delete(role_id)
        logger.info("delete_role_success", role_id=role_id)

    async def is_role_in_use(self, role_id: int) -> bool:
        count = await self.repo.count_users_with_role(role_id)
        in_use = count > 0
        logger.info("is_role_in_use_checked", role_id=role_id, in_use=in_use)
        return in_use