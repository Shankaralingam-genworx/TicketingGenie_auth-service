"""Pydantic schemas for admin staff & team management."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Staff ─────────────────────────────────────────────────────────────────────

class CreateStaffRequest(BaseModel):
    name:  str    = Field(..., min_length=1)
    email: EmailStr
    # Restricted to staff roles only — prevents accidentally creating admin/customer
    # accounts through this endpoint and avoids the ValueError→500 bug.
    role:  Literal["support_agent", "team_lead"] = Field(
        ..., description="Must be 'support_agent' or 'team_lead'"
    )


class StaffResponse(BaseModel):
    id:         int
    name:       str
    email:      str
    role:       str
    is_active:  bool
    team_id:    Optional[int] = None
    team_name:  Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Teams ─────────────────────────────────────────────────────────────────────

class CreateTeamRequest(BaseModel):
    name:         str       = Field(..., min_length=1, max_length=100)
    team_lead_id: int       = Field(..., description="User ID of the team lead")
    agent_ids:    list[int] = Field(
        default_factory=list, description="Support agent user IDs to add as members"
    )


class UpdateTeamRequest(BaseModel):
    name:             Optional[str]       = None
    team_lead_id:     Optional[int]       = None
    add_agent_ids:    Optional[list[int]] = None
    remove_agent_ids: Optional[list[int]] = None


class TeamMemberInfo(BaseModel):
    user_id: int
    name:    str
    email:   str
    role:    str

    model_config = {"from_attributes": True}


class TeamDetailResponse(BaseModel):
    id:           int
    name:         str
    team_lead_id: int
    team_lead:    Optional[TeamMemberInfo] = None
    members:      list[TeamMemberInfo]     = Field(default_factory=list)
    created_at:   datetime

    model_config = {"from_attributes": True}


class TeamDropdownItem(BaseModel):
    id:           int
    name:         str
    team_lead_id: int

    model_config = {"from_attributes": True}