"""Customer database model (extends users with role=CUSTOMER).

⚠️  CustomerTier here must use the SAME values as CustomerTier in the ticket
    service (src/constants/sla_constants.py). Both map to the SQL type
    'customertier' created in V1__create_auth_service_tables.sql.
    Align both Python Enum classes before running migrations.
"""

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
        # Explicit name matches the SQL enum type created in V1
        SAEnum(PreferredContact, name="preferredcontact"), nullable=True
    )

    customer_tier: Mapped[CustomerTier] = mapped_column(
        # Explicit name matches the SQL enum type created in V1
        # and reused in ticket service (sla_policies, tickets tables)
        SAEnum(CustomerTier, name="customertier"), nullable=False, default=CustomerTier.SMB
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="customer")  # noqa: F821