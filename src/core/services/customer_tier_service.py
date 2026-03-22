"""Business logic for customer tier management."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.base_exception import AppException, NotFoundException
from src.data.repositories.customer_tier_repository import CustomerTierRepository
from src.data.models.postgres.customer_tier_model import CustomerTier
from src.schemas.customer_tier_schema import (
    CustomerTierCreate,
    CustomerTierResponse,
    CustomerTierUpdate,
)
from src.observability.logging.logger import get_logger

# Logger with service context
logger = get_logger(__name__).bind(service="auth-service")


class CustomerTierService:

    def __init__(self, db: AsyncSession):
        self.repo = CustomerTierRepository(db)

    async def get_all(self) -> list[CustomerTierResponse]:
        """Return all tiers."""
        logger.info("list_tiers_started")

        tiers = await self.repo.get_all()

        logger.info("list_tiers_success", count=len(tiers))
        return [CustomerTierResponse.model_validate(t) for t in tiers]

    async def get_by_id(self, tier_id: int) -> CustomerTier:
        """Fetch tier by id."""
        logger.info("get_tier_started", tier_id=tier_id)

        tier = await self.repo.get_by_id(tier_id)
        if not tier:
            logger.warning("get_tier_not_found", tier_id=tier_id)
            raise NotFoundException("CustomerTier", tier_id)

        logger.info("get_tier_success", tier_id=tier_id)
        return tier

    async def create(self, payload: CustomerTierCreate) -> CustomerTierResponse:
        """Create new tier."""
        logger.info("create_tier_started")

        # Check duplicate name
        existing = await self.repo.get_by_name(payload.name)
        if existing:
            logger.warning("create_tier_name_conflict")
            raise AppException(
                f"Customer tier '{payload.name}' already exists.", status_code=409
            )

        tier = await self.repo.create(
            name=payload.name,
            description=payload.description,
        )

        logger.info("create_tier_success", tier_id=tier.id)
        return CustomerTierResponse.model_validate(tier)

    async def update(
        self, tier_id: int, payload: CustomerTierUpdate
    ) -> CustomerTierResponse:
        """Update tier."""
        logger.info("update_tier_started", tier_id=tier_id)

        tier = await self.get_by_id(tier_id)

        # Prevent duplicate rename
        if payload.name:
            conflict = await self.repo.get_by_name(payload.name)
            if conflict and conflict.id != tier_id:
                logger.warning("update_tier_name_conflict", tier_id=tier_id)
                raise AppException(
                    f"Customer tier '{payload.name}' already exists.", status_code=409
                )

        updated = await self.repo.update(
            tier,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )

        logger.info("update_tier_success", tier_id=tier_id)
        return CustomerTierResponse.model_validate(updated)

    async def delete(self, tier_id: int) -> None:
        """Delete tier if unused."""
        logger.info("delete_tier_started", tier_id=tier_id)

        tier = await self.get_by_id(tier_id)

        # Count references
        cust_count = await self.repo.count_customers_using(tier_id)
        org_count = await self.repo.count_organisations_using(tier_id)

        if cust_count > 0 or org_count > 0:
            logger.warning(
                "delete_tier_blocked",
                tier_id=tier_id,
                customers=cust_count,
                organisations=org_count,
            )
            raise AppException(
                "Cannot delete tier — still in use.",
                status_code=409,
            )

        await self.repo.delete(tier)

        logger.info("delete_tier_success", tier_id=tier_id)