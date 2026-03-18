
from sqlalchemy import ForeignKey, String, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.postgres_client import Base
from src.constants.customer_constants import PreferredContact


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )

    # Mirrors users.org_id — denormalised for ticket-service joins
    org_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organisations.id"), nullable=True, default=None
    )

    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    preferred_contact: Mapped[PreferredContact | None] = mapped_column(
        SAEnum(PreferredContact, name="preferredcontact"), nullable=True
    )

    # FK-based tier — replaces the old enum column
    customer_tier_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customer_tiers.id"), nullable=True, default=None
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="customer"
    )

    # back_populates="customers" matches Organisation.customers
    organisation: Mapped["Organisation"] = relationship(  # noqa: F821
        "Organisation", back_populates="customers", foreign_keys=[org_id]
    )

    # back_populates="customers" matches CustomerTier.customers
    tier: Mapped["CustomerTier"] = relationship(  # noqa: F821
        "CustomerTier", back_populates="customers", foreign_keys=[customer_tier_id]
    )