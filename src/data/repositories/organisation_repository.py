"""Repository for organisation database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.postgres.organisation_model import Organisation
from src.data.models.postgres.user_model import User

from src.data.models.postgres.customer_model import Customer
from src.data.models.postgres.role_model import Role

class OrganisationRepository:
    """All DB operations for the organisations table."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Query helpers ──────────────────────────────────────────────────────────

    def _base_query(self):
        return select(Organisation).options(
            selectinload(Organisation.tier)
        )

    # ── CRUD ───────────────────────────────────────────────────────────────────

    async def get_all(self) -> list[Organisation]:
        result = await self.db.execute(
            self._base_query().order_by(Organisation.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, org_id: int) -> Organisation | None:
        result = await self.db.execute(
            self._base_query().where(Organisation.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Organisation | None:
        result = await self.db.execute(
            select(Organisation).where(Organisation.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Organisation | None:
        """Check if a domain is already taken by another organisation."""
        result = await self.db.execute(
            select(Organisation).where(Organisation.domain == domain)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        customer_tier_id: int | None = None,
        domain: str | None = None,
    ) -> Organisation:
        org = Organisation(
            name=name,
            customer_tier_id=customer_tier_id,
            domain=domain,
        )
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def update(
        self,
        org: Organisation,
        name: str | None = None,
        customer_tier_id: int | None = None,
        domain: str | None = None,
        is_active: bool | None = None,
    ) -> Organisation:
        if name is not None:
            org.name = name
        if customer_tier_id is not None:
            org.customer_tier_id = customer_tier_id
        if domain is not None:
            org.domain = domain
        if is_active is not None:
            org.is_active = is_active
        await self.db.flush()
        await self.db.refresh(org)
        return org

    # ── Org-scoped user queries ────────────────────────────────────────────────

    async def get_org_admin(self, org_id: int) -> User | None:
        """Return the org_admin user for this organisation."""
        result = await self.db.execute(
            select(User)
            .join(Role, User.role_id == Role.id)
            .options(selectinload(User.role))
            .where(User.org_id == org_id, Role.name == "org_admin")
        )
        return result.scalar_one_or_none()

    async def get_customers(self, org_id: int) -> list[User]:
        """Return all customer users in this organisation."""
        result = await self.db.execute(
            select(User)
            .join(Role, User.role_id == Role.id)
            .options(
                selectinload(User.role),
                selectinload(User.customer).selectinload(Customer.tier),
            )
            .where(User.org_id == org_id, Role.name == "customer")
            .order_by(User.id)
        )
        return list(result.scalars().all())