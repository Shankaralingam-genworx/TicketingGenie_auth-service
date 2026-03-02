"""Business logic for customer profile operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.auth_exceptions import UserNotFoundException
from src.data.repositories.customer_repository import CustomerRepository
from src.data.repositories.user_repository import UserRepository
from src.schemas.customer_schema import CurrentUserResponse, CustomerProfileResponse


class CustomerService:
    """Handles customer profile business logic."""

    def __init__(self, db: AsyncSession):
        self.customer_repo = CustomerRepository(db)
        self.user_repo = UserRepository(db)

    async def get_current_user_profile(self, user_id: str) -> CurrentUserResponse:
        """Fetch the full profile of the currently logged-in user."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        customer_profile = None
        if user.customer:
            customer_profile = CustomerProfileResponse(
                id=user.customer.id,
                user_id=user.customer.user_id,
                phone=user.customer.phone,
                company_name=user.customer.company_name,
                created_at=user.customer.created_at
            )

        return CurrentUserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role.name,
            is_active=user.is_active,
            created_at=user.created_at,
            customer_profile=customer_profile,
        )
