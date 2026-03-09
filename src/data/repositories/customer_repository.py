"""Repository for customer-related database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.customer_model import Customer
from src.constants.customer_constants import CustomerTier, PreferredContact


class CustomerRepository:
    """Handles all DB operations for customers."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: int) -> Customer | None:
        """Fetch a customer record by user_id."""
        result = await self.db.execute(
            select(Customer).where(Customer.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        phone: str | None = None,
        customer_tier: CustomerTier = CustomerTier.SMB,
        preferred_contact: PreferredContact = PreferredContact.EMAIL,
    ) -> Customer:
        """Create a customer profile linked to a user, with tier and contact preference."""
        customer = Customer(
            user_id=user_id,
            phone=phone,
            customer_tier=customer_tier,
            preferred_contact=preferred_contact,
        )
        self.db.add(customer)
        await self.db.flush() 
        return customer