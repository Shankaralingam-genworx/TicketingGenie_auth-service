"""User database model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String,Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.utils.auth_utils import get_current_time
from src.data.clients.postgres_client import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: get_current_time()
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="users")  # noqa: F821
    customer: Mapped["Customer"] = relationship(  # noqa: F821
        "Customer", back_populates="user", uselist=False
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # noqa: F821
        "RefreshToken", back_populates="user"
    )
    
    # Teams where user is the team lead
    led_teams: Mapped[list["Team"]] = relationship(  # noqa: F821
        "Team",
        back_populates="team_lead",
        foreign_keys="Team.team_lead_id",
    )
    
    # Teams where user is a member
    team_memberships: Mapped[list["TeamMember"]] = relationship(  # noqa: F821
        "TeamMember",
        back_populates="user",
        cascade="all, delete-orphan",
)

    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(  # noqa: F821
    "PasswordResetToken",
    back_populates="user",
    cascade="all, delete-orphan",
)