"""Repository for user-related database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.postgres.user_model import User
from src.data.models.postgres.customer_model import Customer
from src.data.models.postgres.team_member_model import TeamMember


class UserRepository:
    """Handles all DB operations for users."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Queries ────────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: int) -> User | None:
      
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.role),
                selectinload(User.customer).selectinload(Customer.tier),
                selectinload(User.organisation),
                selectinload(User.led_teams),
                selectinload(User.team_memberships).selectinload(TeamMember.team),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.role),
                selectinload(User.customer).selectinload(Customer.tier),
                selectinload(User.led_teams),
                selectinload(User.organisation),
                selectinload(User.team_memberships).selectinload(TeamMember.team),
            )
            .where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[User]:
    
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.role),
                selectinload(User.organisation),
            )
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_roles(self, role_names: list[str]) -> list[User]:
        """Fetch all users whose role.name is in the given list."""
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

    # ── Writes ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        role_id: int,
        org_id: int | None = None,
        must_change_password: bool = False,
    ) -> User:
        
        user = User(
            name=name,
            email=email.lower().strip(),
            password_hash=password_hash,
            role_id=role_id,
            org_id=org_id,
            must_change_password=must_change_password,
        )
        self.db.add(user)
        await self.db.flush()
        return await self.get_by_id(user.id)

    async def create_org_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        role_id: int,
        org_id: int,
    ) -> User:
        
        if not org_id:
            raise ValueError("org_id is required when creating an organisation user.")

        user = User(
            name=name,
            email=email.lower().strip(),
            password_hash=password_hash,
            role_id=role_id,
            org_id=org_id,
            must_change_password=True,
        )
        self.db.add(user)
        await self.db.flush()
        return await self.get_by_id(user.id)

    async def update_password(
        self,
        user_id: int,
        new_password_hash: str,
    ) -> User:
       
        from src.core.exceptions.auth_exceptions import UserNotFoundException

        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        user.password_hash        = new_password_hash
        user.must_change_password = False
        await self.db.flush()
        return user