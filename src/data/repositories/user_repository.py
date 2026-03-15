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
        """
        Fetch a user by ID with all needed relationships loaded eagerly.

        Loads: role, customer+tier, organisation, led_teams, team_memberships.

        led_teams is needed by auth_service.refresh_access_token() for team_lead/agent.
        team_memberships is needed by admin_service.get_staff() and team_service.
        """
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
        """
        Fetch a user by email with all needed relationships loaded eagerly.
        Email comparison is case-insensitive (lowercased before query).
        """
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
        """
        Fetch all users with role and organisation loaded.
        organisation is required by UserService._map() for org_name.
        """
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
        """
        Generic user create — works for all roles.
        Email is normalised to lowercase before storage.
        For org_admin / customer accounts use create_org_user() instead.
        """
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
        """
        Create an org_admin or customer user that belongs to an organisation.

        - org_id is REQUIRED — raises ValueError if missing
        - must_change_password is always True (temp password generated)
        - Email is normalised to lowercase before storage

        Called by OrganisationService.create_organisation() and add_customer().
        """
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
        """
        Replace a user's password hash and clear must_change_password.
        Called by UserService.change_password() after verifying the request.
        """
        from src.core.exceptions.auth_exceptions import UserNotFoundException

        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        user.password_hash        = new_password_hash
        user.must_change_password = False
        await self.db.flush()
        return user