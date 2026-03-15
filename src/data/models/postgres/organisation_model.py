"""Organisation database model.

An Organisation groups customers under a single entity.
Each org has one org_admin user (role=org_admin) and N customer users.
The customer tier is set at the org level — all customers inherit it.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.postgres_client import Base
from src.utils.auth_utils import get_current_time


class Organisation(Base):
    __tablename__ = "organisations"
    __table_args__ = (
        UniqueConstraint("domain", name="uq_organisations_domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    # Optional domain — when set, all org users must have emails @this domain
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # FK to customer_tiers — all customers in this org inherit this tier
    customer_tier_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customer_tiers.id"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: get_current_time()
    )

    # ── Relationships ──────────────────────────────────────────────────────────

    # The tier assigned to this organisation
    tier: Mapped["CustomerTier"] = relationship(  # noqa: F821
        "CustomerTier", back_populates="organisations", foreign_keys=[customer_tier_id]
    )

    # All users (org_admin + customers) whose org_id points here
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", back_populates="organisation", foreign_keys="User.org_id"
    )

    # Shortcut to customer profiles for this org
    customers: Mapped[list["Customer"]] = relationship(  # noqa: F821
        "Customer", back_populates="organisation", foreign_keys="Customer.org_id"
    )