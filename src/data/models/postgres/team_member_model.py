"""Team Member database model."""


from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint,Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.postgres_client import Base
from src.utils.auth_utils import get_current_time

class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    

    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: get_current_time()
    )

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_user"),
    )

    # Relationships
    team: Mapped["Team"] = relationship(  # noqa: F821
        "Team",
        back_populates="members",
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="team_memberships",
    )