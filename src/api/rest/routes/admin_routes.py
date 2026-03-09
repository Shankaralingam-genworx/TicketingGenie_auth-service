"""
Admin routes — staff creation, team management.

POST /admin/staff          Create support agent or team lead (sends welcome email)
GET  /admin/staff          List all staff (agents + leads)
GET  /admin/staff/:id      Get single staff member

POST /admin/teams          Create a team and assign a team lead
GET  /admin/teams          List all teams
GET  /admin/teams/:id      Get team detail
PATCH /admin/teams/:id     Update team (rename, change lead, add/remove members)
DELETE /admin/teams/:id    Delete team
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import require_role
from src.core.services.admin_service import AdminService
from src.data.clients.postgres_client import get_db
from src.schemas.admin_schema import (
    CreateStaffRequest,
    StaffResponse,
    CreateTeamRequest,
    TeamDropdownItem,
    UpdateTeamRequest,
    TeamDetailResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Staff ─────────────────────────────────────────────────────────────────────

@router.post("/staff", response_model=StaffResponse, status_code=201)
async def create_staff(
    data: CreateStaffRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a SUPPORT_AGENT or TEAM_LEAD account.
    Generates a random password, emails it to the new user, and returns the profile.
    """
    service = AdminService(db)
    return await service.create_staff(data)


@router.get("/staff", response_model=list[StaffResponse])
async def list_staff(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all support agents and team leads."""
    service = AdminService(db)
    return await service.list_staff()


@router.get("/staff/{user_id}", response_model=StaffResponse)
async def get_staff(
    user_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_staff(user_id)


# ── Teams ─────────────────────────────────────────────────────────────────────

@router.post("/teams", response_model=TeamDetailResponse, status_code=201)
async def create_team(
    data: CreateTeamRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new team, assign a team lead, and optionally add agent members."""
    service = AdminService(db)
    return await service.create_team(data)


@router.get("/teams", response_model=list[TeamDetailResponse])
async def list_teams(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_teams()


@router.get("/teams/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_team(team_id)


@router.patch("/teams/{team_id}", response_model=TeamDetailResponse)
async def update_team(
    team_id: int,
    data: UpdateTeamRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update team: rename, change team lead, add or remove member agents.
    All fields optional — only provided fields are updated.
    """
    service = AdminService(db)
    return await service.update_team(team_id, data)


@router.delete("/teams/{team_id}", status_code=204)
async def delete_team(
    team_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    await service.delete_team(team_id)
    
@router.get("/teams_dropdown", response_model=list[TeamDropdownItem])
async def teams_dropdown(
    current_user: dict     = Depends(require_role("admin")),
    db:           AsyncSession = Depends(get_db),
):
    """Lightweight team list for dropdowns — id, name, team_lead_id only."""
    service = AdminService(db)
    return await service.list_teams_dropdown()