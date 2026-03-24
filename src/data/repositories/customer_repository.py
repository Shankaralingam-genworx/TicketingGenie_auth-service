"""Repository for customer-related database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.postgres.customer_model import Customer
from src.constants.customer_constants import PreferredContact


class CustomerRepository:
    """Handles all DB operations for customers."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Queries ────────────────────────────────────────────────────────────────

    async def get_by_user_id(self, user_id: int) -> Customer | None:
        """Fetch a customer record by user_id, with tier loaded."""
        result = await self.db.execute(
            select(Customer)
            .options(selectinload(Customer.tier))
            .where(Customer.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_org_id(self, org_id: int) -> list[Customer]:
        """Fetch all customer records for a given organisation."""
        result = await self.db.execute(
            select(Customer)
            .options(selectinload(Customer.tier))
            .where(Customer.org_id == org_id)
        )
        return list(result.scalars().all())

    # ── Writes ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: int,
        org_id: int | None = None,
        phone: str | None = None,
        preferred_contact: PreferredContact | None = PreferredContact.EMAIL,
        customer_tier_id: int | None = None,
    ) -> Customer:
        """
        Generic customer profile create.
        For org-member customers use create_org_customer() instead.
        """
        customer = Customer(
            user_id=user_id,
            org_id=org_id,
            phone=phone,
            preferred_contact=preferred_contact,
            customer_tier_id=customer_tier_id,
        )
        self.db.add(customer)
        await self.db.flush()
        return await self.get_by_user_id(user_id)

    async def create_org_customer(
        self,
        user_id: int,
        org_id: int,
        customer_tier_id: int | None,
        phone: str | None = None,
        preferred_contact: PreferredContact | None = PreferredContact.EMAIL,
    ) -> Customer:
        
        if not org_id:
            raise ValueError("org_id is required when creating an organisation customer.")

        customer = Customer(
            user_id=user_id,
            org_id=org_id,
            phone=phone,
            preferred_contact=preferred_contact,
            customer_tier_id=customer_tier_id,  # inherited from org
        )
        self.db.add(customer)
        await self.db.flush()
        return await self.get_by_user_id(user_id)