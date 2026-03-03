"""Role database model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String,Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.postgres_client import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="role")  # noqa: F821
