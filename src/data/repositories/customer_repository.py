"""Repository for customer-related database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.customer_model import Customer


class CustomerRepository:
    """Handles all DB operations for customers."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: str) -> Customer | None:
        """Fetch a customer record by user_id."""
        result = await self.db.execute(
            select(Customer).where(Customer.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: str,
        phone: str | None = None,
        company_name: str | None = None
    ) -> Customer:
        """Create a customer profile linked to a user."""
        customer = Customer(
            user_id=user_id, phone=phone, company_name=company_name
        )
        self.db.add(customer)
        await self.db.flush()
        return customer
