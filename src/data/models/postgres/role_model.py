"""Role database model."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String,Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.postgres_client import Base
from src.utils.auth_utils import get_current_time


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: get_current_time()
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="role")  # noqa: F821
