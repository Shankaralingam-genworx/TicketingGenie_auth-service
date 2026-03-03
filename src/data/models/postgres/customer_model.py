"""Customer database model (extends users with role=CUSTOMER)."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.postgres_client import Base
from src.constants.customer_constants import CustomerTier, PreferredContact 


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    preferred_contact: Mapped[PreferredContact | None] = mapped_column(
        SAEnum(PreferredContact), nullable=True
    )
    
    customer_tier: Mapped[CustomerTier] = mapped_column(
        SAEnum(CustomerTier), nullable=False, default=CustomerTier.BASIC
    )
    


    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="customer")  # noqa: F821