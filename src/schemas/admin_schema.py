"""Pydantic schemas for admin staff & team management."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from src.constants.auth_constants import RoleName


# ── Staff ─────────────────────────────────────────────────────────────────────

class CreateStaffRequest(BaseModel):
    name:  str       = Field(..., min_length=1)
    email: EmailStr
    role:  RoleName  = Field(..., description="SUPPORT_AGENT or TEAM_LEAD")

    class Config:
        # Only these roles are valid for staff creation
        @staticmethod
        def schema_extra(schema, _):
            schema["properties"]["role"]["enum"] = [
                RoleName.SUPPORT_AGENT.value,
                RoleName.TEAM_LEAD.value,
            ]


class StaffResponse(BaseModel):
    id:         int
    name:       str
    email:      str
    role:       str
    is_active:  bool
    team_id:    Optional[int]
    team_name:  Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Teams ─────────────────────────────────────────────────────────────────────

class CreateTeamRequest(BaseModel):
    name:         str       = Field(..., min_length=1, max_length=100)
    team_lead_id: int       = Field(..., description="User ID of the team lead")
    agent_ids:    list[int] = Field(default_factory=list, description="Agent user IDs to add as members")


class UpdateTeamRequest(BaseModel):
    name:              Optional[str]       = None
    team_lead_id:      Optional[int]       = None
    add_agent_ids:     Optional[list[int]] = None   # agents to add
    remove_agent_ids:  Optional[list[int]] = None   # agents to remove


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
    team_lead:    Optional[TeamMemberInfo]
    members:      list[TeamMemberInfo]
    created_at:   datetime

    model_config = {"from_attributes": True}
    
    
class TeamDropdownItem(BaseModel):
    id:           int
    name:         str
    team_lead_id: int

    model_config = {"from_attributes": True}