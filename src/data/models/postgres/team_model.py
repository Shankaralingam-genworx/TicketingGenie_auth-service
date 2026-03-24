"""Team database model."""


from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String,Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.postgres_client import Base
from src.utils.auth_utils import get_current_time


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)


    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    team_lead_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: get_current_time()
    )

    # Relationships
    team_lead: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="led_teams",
        foreign_keys=[team_lead_id],
    )

    members: Mapped[list["TeamMember"]] = relationship(  # noqa: F821
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
    )