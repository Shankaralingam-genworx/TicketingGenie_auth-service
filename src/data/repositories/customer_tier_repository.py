"""Repository for customer tier database operations."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.customer_tier_model import CustomerTier
from src.data.models.postgres.customer_model import Customer


class CustomerTierRepository:
    """All DB operations for the customer_tiers table."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[CustomerTier]:
        result = await self.db.execute(
            select(CustomerTier).order_by(CustomerTier.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, tier_id: int) -> CustomerTier | None:
        result = await self.db.execute(
            select(CustomerTier).where(CustomerTier.id == tier_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> CustomerTier | None:
        result = await self.db.execute(
            select(CustomerTier).where(CustomerTier.name == name)
        )
        return result.scalar_one_or_none()

    async def create(
        self, name: str, description: str | None = None
    ) -> CustomerTier:
        tier = CustomerTier(name=name, description=description)
        self.db.add(tier)
        await self.db.flush()
        await self.db.refresh(tier)
        return tier

    async def update(
        self,
        tier: CustomerTier,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> CustomerTier:
        if name is not None:
            tier.name = name
        if description is not None:
            tier.description = description
        if is_active is not None:
            tier.is_active = is_active
        await self.db.flush()
        await self.db.refresh(tier)
        return tier

    async def delete(self, tier: CustomerTier) -> None:
        await self.db.delete(tier)
        await self.db.flush()

    async def count_customers_using(self, tier_id: int) -> int:
        """Return how many customer profiles reference this tier."""
        result = await self.db.execute(
            select(func.count()).where(Customer.customer_tier_id == tier_id)
        )
        return result.scalar_one()

    async def count_organisations_using(self, tier_id: int) -> int:
      
        from src.data.models.postgres.organisation_model import Organisation

        result = await self.db.execute(
            select(func.count()).where(Organisation.customer_tier_id == tier_id)
        )
        return result.scalar_one()