from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import require_role
from src.core.services.team_service import TeamService
from src.data.clients.postgres_client import get_db
from src.schemas.admin_schema import StaffResponse, TeamDetailResponse

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("/my-agents", response_model=list[StaffResponse])
async def my_agents(
    current_user: dict = Depends(require_role("team_lead")),
    db: AsyncSession = Depends(get_db),
):
    """Return all SUPPORT_AGENT members of the team lead's team."""
    service = TeamService(db)
    return await service.get_agents_for_lead(current_user.get("team_id"))


@router.get("/me", response_model=TeamDetailResponse)
async def my_team(
    current_user: dict = Depends(require_role("team_lead", "support_agent")),
    db: AsyncSession = Depends(get_db),
):
    """Return the team the current user belongs to."""
    service = TeamService(db)
    return await service.get_team_for_user(current_user.get("team_id"))