"""Team data access for team lead and agent portals."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.core.exceptions.base_exception import NotFoundException
from src.data.repositories.team_repository import TeamRepository
from src.schemas.admin_schema import StaffResponse, TeamDetailResponse, TeamMemberInfo
from src.observability.logging.logger import get_logger

logger = get_logger(__name__).bind(service="auth-service")


class TeamService:

    def __init__(self, db: AsyncSession):
        self.team_repo = TeamRepository(db)

    async def get_agents_for_lead(self, team_id: int | None) -> list[StaffResponse]:
        """Return all support agents in the team lead's team."""
        if not team_id:
            return []

        logger.info("get_agents_for_lead_started", team_id=team_id)

        team = await self.team_repo.get_by_id(team_id)
        if not team:
            logger.warning("get_agents_for_lead_team_not_found", team_id=team_id)
            raise NotFoundException("Team", team_id)

        agents = [
            StaffResponse(
                id=m.user.id,
                name=m.user.name,
                email=m.user.email,
                role=m.user.role.name,
                is_active=m.user.is_active,
                team_id=team.id,
                team_name=team.name,
                created_at=m.user.created_at,
            )
            for m in team.members
            if m.user.role.name == RoleName.SUPPORT_AGENT.value
        ]

        logger.info("get_agents_for_lead_success", team_id=team_id, count=len(agents))
        return agents

    async def get_team_for_user(self, team_id: int | None) -> TeamDetailResponse:
        """Return team details for a team lead or support agent."""
        if not team_id:
            logger.warning("get_team_for_user_no_team_id")
            raise NotFoundException("Team", 0)

        logger.info("get_team_for_user_started", team_id=team_id)

        team = await self.team_repo.get_by_id(team_id)
        if not team:
            logger.warning("get_team_for_user_not_found", team_id=team_id)
            raise NotFoundException("Team", team_id)

        lead_info = (
            TeamMemberInfo(
                user_id=team.team_lead.id,
                name=team.team_lead.name,
                email=team.team_lead.email,
                role=team.team_lead.role.name,
            )
            if team.team_lead else None
        )

        members = [
            TeamMemberInfo(
                user_id=m.user.id,
                name=m.user.name,
                email=m.user.email,
                role=m.user.role.name,
            )
            for m in team.members
        ]

        logger.info("get_team_for_user_success", team_id=team_id)

        return TeamDetailResponse(
            id=team.id,
            name=team.name,
            team_lead_id=team.team_lead_id,
            team_lead=lead_info,
            members=members,
            created_at=team.created_at,
        )