"""Business logic for customer profile operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.auth_exceptions import UserNotFoundException
from src.data.repositories.user_repository import UserRepository
from src.schemas.customer_schema import CurrentUserResponse, CustomerProfileResponse
from src.schemas.customer_tier_schema import CustomerTierResponse


class CustomerService:
    """Handles customer profile business logic."""

    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)

    async def get_current_user_profile(self, user_id: str) -> CurrentUserResponse:
        """Fetch the full profile of the currently logged-in user (any role)."""
        user = await self.user_repo.get_by_id(int(user_id))
        if not user:
            raise UserNotFoundException()

        customer_profile = None
        if user.customer:
            c = user.customer
            customer_profile = CustomerProfileResponse(
                id=c.id,
                user_id=c.user_id,
                org_id=c.org_id,
                phone=c.phone,
                preferred_contact=c.preferred_contact,
                customer_tier_id=c.customer_tier_id,
                tier=(
                    CustomerTierResponse.model_validate(c.tier) if c.tier else None
                ),
            )

        return CurrentUserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role.name,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            org_id=user.org_id,
            org_name=user.organisation.name if user.organisation else None,
            created_at=user.created_at,
            customer_profile=customer_profile,
        )