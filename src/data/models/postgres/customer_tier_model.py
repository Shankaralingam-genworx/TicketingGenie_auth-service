"""CustomerTier database model.

Replaces the hard-coded CustomerTier enum with a DB table so the system
admin can add/rename/deactivate tiers without a code deploy.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.postgres_client import Base
from src.utils.auth_utils import get_current_time


class CustomerTier(Base):
    __tablename__ = "customer_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: get_current_time()
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    organisations: Mapped[list["Organisation"]] = relationship(  # noqa: F821
        "Organisation", back_populates="tier"
    )

    customers: Mapped[list["Customer"]] = relationship(  # noqa: F821
        "Customer", back_populates="tier"
    )