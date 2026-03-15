"""Business logic for customer tier management."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.repositories.customer_tier_repository import CustomerTierRepository
from src.data.models.postgres.customer_tier_model import CustomerTier
from src.schemas.customer_tier_schema import (
    CustomerTierCreate,
    CustomerTierResponse,
    CustomerTierUpdate,
)


class CustomerTierService:

    def __init__(self, db: AsyncSession):
        self.repo = CustomerTierRepository(db)

    async def get_all(self) -> list[CustomerTierResponse]:
        tiers = await self.repo.get_all()
        return [CustomerTierResponse.model_validate(t) for t in tiers]

    async def get_by_id(self, tier_id: int) -> CustomerTier:
        tier = await self.repo.get_by_id(tier_id)
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer tier not found.",
            )
        return tier

    async def create(self, payload: CustomerTierCreate) -> CustomerTierResponse:
        existing = await self.repo.get_by_name(payload.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Customer tier '{payload.name}' already exists.",
            )
        tier = await self.repo.create(
            name=payload.name,
            description=payload.description,
        )
        return CustomerTierResponse.model_validate(tier)

    async def update(
        self, tier_id: int, payload: CustomerTierUpdate
    ) -> CustomerTierResponse:
        tier = await self.get_by_id(tier_id)
        if payload.name:
            conflict = await self.repo.get_by_name(payload.name)
            if conflict and conflict.id != tier_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Customer tier '{payload.name}' already exists.",
                )
        updated = await self.repo.update(
            tier,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )
        return CustomerTierResponse.model_validate(updated)

    async def delete(self, tier_id: int) -> None:
        tier = await self.get_by_id(tier_id)

        # Check both customers AND organisations before deleting.
        # The DB FK on organisations.customer_tier_id has no ondelete="CASCADE"
        # so deleting a tier still referenced by an org raises an IntegrityError.
        cust_count = await self.repo.count_customers_using(tier_id)
        org_count  = await self.repo.count_organisations_using(tier_id)

        if cust_count > 0 or org_count > 0:
            parts = []
            if cust_count:
                parts.append(f"{cust_count} customer(s)")
            if org_count:
                parts.append(f"{org_count} organisation(s)")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete tier — it is still used by {' and '.join(parts)}.",
            )

        await self.repo.delete(tier)