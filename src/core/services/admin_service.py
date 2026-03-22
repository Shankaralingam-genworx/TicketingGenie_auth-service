"""Admin service — staff creation with welcome email, team CRUD."""

import secrets
import string

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.core.exceptions.auth_exceptions import UserAlreadyExistsException
from src.core.exceptions.base_exception import AppException, NotFoundException
from src.core.security import hash_password
from src.core.celery.workers.email_tasks import send_staff_welcome_email
from src.data.repositories.role_repository import RoleRepository
from src.data.repositories.team_repository import TeamRepository
from src.data.repositories.user_repository import UserRepository
from src.schemas.admin_schema import (
    CreateStaffRequest,
    CreateTeamRequest,
    StaffResponse,
    TeamDetailResponse,
    TeamMemberInfo,
    UpdateTeamRequest,
)
from src.observability.logging.logger import get_logger

# Bind "service" so every log from this module carries service="admin-service" in GCP
logger = get_logger(__name__).bind(service="auth-service")

# Roles that are considered "staff" — used as a guard in create_staff
STAFF_ROLES = {RoleName.SUPPORT_AGENT.value, RoleName.TEAM_LEAD.value}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _generate_password(length: int = 12) -> str:
    """
    Generate a cryptographically secure random password.
    Guarantees at least one uppercase, lowercase, digit, and symbol.
    Never logged — only sent via email to the new staff member.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    # Seed with one char from each required class, then fill the rest randomly
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    pwd += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)


def _to_staff_response(user, team_id=None, team_name=None) -> StaffResponse:
    """Map a User ORM object → StaffResponse schema."""
    return StaffResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        team_id=team_id,
        team_name=team_name,
        created_at=user.created_at,
    )


def _to_team_detail(team) -> TeamDetailResponse:
    """Map a Team ORM object (with loaded relationships) → TeamDetailResponse."""
    lead_info = (
        TeamMemberInfo(
            user_id=team.team_lead.id,
            name=team.team_lead.name,
            email=team.team_lead.email,
            role=team.team_lead.role.name,
        )
        if team.team_lead
        else None
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

    return TeamDetailResponse(
        id=team.id,
        name=team.name,
        team_lead_id=team.team_lead_id,
        team_lead=lead_info,
        members=members,
        created_at=team.created_at,
    )


# ── Service ────────────

class AdminService:
    def __init__(self, db: AsyncSession):
        self.db        = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.team_repo = TeamRepository(db)

    # ── Staff ──────────────

    async def create_staff(self, data: CreateStaffRequest) -> StaffResponse:
        """
        Create a new SUPPORT_AGENT or TEAM_LEAD account.
        Generates a temp password, emails it via Celery, and sets must_change_password=True.
        """
        logger.info("create_staff_started", role=data.role)

        # Defensive role check — schema Literal already limits values, but guard anyway
        if data.role not in STAFF_ROLES:
            logger.warning("create_staff_invalid_role", role=data.role)
            raise AppException(f"Role must be one of {STAFF_ROLES}", status_code=400)

        # Reject duplicate emails early — avoids a DB unique-constraint error later
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            logger.warning("create_staff_email_already_exists")
            raise UserAlreadyExistsException()

        # Roles must be seeded in the DB; missing role means a setup problem
        role = await self.role_repo.get_by_name(data.role)
        if not role:
            logger.error("create_staff_role_not_seeded", role=data.role)
            raise AppException(f"Role '{data.role}' not seeded.", status_code=500)

        # Hash before persisting — plain password only lives in memory briefly
        plain_password = _generate_password()
        user = await self.user_repo.create(
            name=data.name,
            email=data.email,
            password_hash=hash_password(plain_password),
            role_id=role.id,
            must_change_password=True,  # Force password reset on first login
        )

        # Celery task — fire-and-forget so the API response is not blocked by SMTP
        send_staff_welcome_email.delay(
            to_email=data.email,
            name=data.name,
            role=data.role,
            temp_password=plain_password,  # Only sent via email, never logged
        )

        logger.info("create_staff_success", user_id=user.id, role=data.role)
        return _to_staff_response(user)

    async def get_staff(self, user_id: int) -> StaffResponse:
        """Fetch a single staff member by ID. Raises 404 if not found or not staff."""
        logger.info("get_staff_started", user_id=user_id)

        user = await self.user_repo.get_by_id(user_id)
        if not user or user.role.name not in STAFF_ROLES:
            logger.warning("get_staff_not_found", user_id=user_id)
            raise NotFoundException("Staff", user_id)

        # Resolve team from the first membership (staff belong to at most one team)
        team_id = team_name = None
        if user.team_memberships:
            m         = user.team_memberships[0]
            team_id   = m.team_id
            team_name = m.team.name if m.team else None

        logger.info("get_staff_success", user_id=user_id)
        return _to_staff_response(user, team_id, team_name)

    async def list_staff(self) -> list[StaffResponse]:
        """Return all support agents and team leads."""
        logger.info("list_staff_started")

        users = await self.user_repo.get_by_roles(
            [RoleName.SUPPORT_AGENT.value, RoleName.TEAM_LEAD.value]
        )

        result = []
        for u in users:
            team_id = team_name = None
            if u.team_memberships:
                m         = u.team_memberships[0]
                team_id   = m.team_id
                team_name = m.team.name if m.team else None
            result.append(_to_staff_response(u, team_id, team_name))

        logger.info("list_staff_success", count=len(result))
        return result

    # ── Teams ───────────────

    async def create_team(self, data: CreateTeamRequest) -> TeamDetailResponse:
        """
        Create a team, assign a lead, and optionally add agent members.
        The lead is always added as a member so their JWT team_id resolves correctly.
        """
        logger.info("create_team_started", team_name=data.name, lead_id=data.team_lead_id)

        # Validate the designated lead exists and has the correct role
        lead = await self.user_repo.get_by_id(data.team_lead_id)
        if not lead or lead.role.name != RoleName.TEAM_LEAD.value:
            logger.warning("create_team_invalid_lead", lead_id=data.team_lead_id)
            raise AppException(
                "team_lead_id must reference a TEAM_LEAD user.", status_code=400
            )

        team = await self.team_repo.create(
            name=data.name,
            team_lead_id=data.team_lead_id,
        )

        # Lead must be a member so their team_id claim in the JWT resolves
        await self.team_repo.add_member(team.id, data.team_lead_id)

        # Validate and add each agent; fail fast if any agent_id is invalid
        for agent_id in data.agent_ids:
            agent = await self.user_repo.get_by_id(agent_id)
            if not agent or agent.role.name != RoleName.SUPPORT_AGENT.value:
                logger.warning(
                    "create_team_invalid_agent", agent_id=agent_id, team_id=team.id
                )
                raise AppException(
                    f"User {agent_id} is not a support agent.", status_code=400
                )
            await self.team_repo.add_member(team.id, agent_id)

        # Re-fetch with relationships loaded so _to_team_detail has full data
        team = await self.team_repo.get_by_id(team.id)
        logger.info("create_team_success", team_id=team.id, team_name=team.name)
        return _to_team_detail(team)

    async def get_team(self, team_id: int) -> TeamDetailResponse:
        """Fetch a single team with its lead and member details."""
        logger.info("get_team_started", team_id=team_id)

        team = await self.team_repo.get_by_id(team_id)
        if not team:
            logger.warning("get_team_not_found", team_id=team_id)
            raise NotFoundException("Team", team_id)

        logger.info("get_team_success", team_id=team_id)
        return _to_team_detail(team)

    async def list_teams(self) -> list[TeamDetailResponse]:
        """Return all teams with full lead and member details."""
        logger.info("list_teams_started")

        teams = await self.team_repo.get_all()

        logger.info("list_teams_success", count=len(teams))
        return [_to_team_detail(t) for t in teams]

    async def update_team(
        self, team_id: int, data: UpdateTeamRequest
    ) -> TeamDetailResponse:
        """
        Partial update: rename, swap lead, add/remove agents.
        Each field is optional — only provided fields are applied.
        Prevents removing the current lead from the member list.
        """
        logger.info("update_team_started", team_id=team_id)

        team = await self.team_repo.get_by_id(team_id)
        if not team:
            logger.warning("update_team_not_found", team_id=team_id)
            raise NotFoundException("Team", team_id)

        # Rename if requested
        if data.name is not None:
            team = await self.team_repo.update(team, name=data.name)
            logger.info("update_team_renamed", team_id=team_id, new_name=data.name)

        # Swap lead if requested — validate new lead role first
        if data.team_lead_id is not None:
            lead = await self.user_repo.get_by_id(data.team_lead_id)
            if not lead or lead.role.name != RoleName.TEAM_LEAD.value:
                logger.warning(
                    "update_team_invalid_lead",
                    team_id=team_id,
                    lead_id=data.team_lead_id,
                )
                raise AppException(
                    "team_lead_id must reference a TEAM_LEAD user.", status_code=400
                )
            team = await self.team_repo.update(team, team_lead_id=data.team_lead_id)
            # Ensure new lead is in the members list so their JWT resolves correctly
            await self.team_repo.add_member(team.id, data.team_lead_id)
            logger.info(
                "update_team_lead_swapped",
                team_id=team_id,
                new_lead_id=data.team_lead_id,
            )

        # Add new agents
        for agent_id in data.add_agent_ids or []:
            agent = await self.user_repo.get_by_id(agent_id)
            if not agent or agent.role.name != RoleName.SUPPORT_AGENT.value:
                logger.warning(
                    "update_team_invalid_agent_add",
                    team_id=team_id,
                    agent_id=agent_id,
                )
                raise AppException(
                    f"User {agent_id} is not a support agent.", status_code=400
                )
            await self.team_repo.add_member(team.id, agent_id)
            logger.info("update_team_agent_added", team_id=team_id, agent_id=agent_id)

        # Remove agents — block removal of the current lead
        for agent_id in data.remove_agent_ids or []:
            if agent_id == team.team_lead_id:
                logger.warning(
                    "update_team_remove_lead_blocked",
                    team_id=team_id,
                    agent_id=agent_id,
                )
                raise AppException(
                    "Cannot remove the team lead from the team members list.",
                    status_code=400,
                )
            await self.team_repo.remove_member(team.id, agent_id)
            logger.info(
                "update_team_agent_removed", team_id=team_id, agent_id=agent_id
            )

        # Re-fetch so the returned object reflects all changes
        team = await self.team_repo.get_by_id(team_id)
        logger.info("update_team_success", team_id=team_id)
        return _to_team_detail(team)

    async def delete_team(self, team_id: int) -> None:
        """Permanently delete a team. Raises 404 if not found."""
        logger.info("delete_team_started", team_id=team_id)

        team = await self.team_repo.get_by_id(team_id)
        if not team:
            logger.warning("delete_team_not_found", team_id=team_id)
            raise NotFoundException("Team", team_id)

        await self.team_repo.delete(team)
        logger.info("delete_team_success", team_id=team_id)

    async def list_teams_dropdown(self) -> list[dict]:
        """Lightweight team list for UI dropdowns — id, name, team_lead_id only."""
        logger.info("list_teams_dropdown_started")

        rows = await self.team_repo.get_all_dropdown()
        result = [
            {"id": r.id, "name": r.name, "team_lead_id": r.team_lead_id}
            for r in rows
        ]

        logger.info("list_teams_dropdown_success", count=len(result))
        return result