"""Admin service — staff creation with welcome email, team CRUD."""

import logging
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

logger = logging.getLogger("admin.service")

STAFF_ROLES = {RoleName.SUPPORT_AGENT.value, RoleName.TEAM_LEAD.value}


def _generate_password(length: int = 12) -> str:
    """
    Generate a secure random password that meets complexity requirements:
    at least one uppercase, one lowercase, one digit, one symbol.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    # Guarantee at least one character from each required class
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
    lead_info = TeamMemberInfo(
        user_id=team.team_lead.id,
        name=team.team_lead.name,
        email=team.team_lead.email,
        role=team.team_lead.role.name,
    ) if team.team_lead else None

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


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db        = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.team_repo = TeamRepository(db)

    # ── Staff ──────────────────────────────────────────────────────────────────

    async def create_staff(self, data: CreateStaffRequest) -> StaffResponse:
        # Schema already restricts role to "support_agent" | "team_lead" via Literal
        # but guard here defensively as well
        if data.role not in STAFF_ROLES:
            raise AppException(f"Role must be one of {STAFF_ROLES}", status_code=400)

        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise UserAlreadyExistsException()

        role = await self.role_repo.get_by_name(data.role)
        if not role:
            raise AppException(f"Role '{data.role}' not seeded.", status_code=500)

        plain_password = _generate_password()
        user = await self.user_repo.create(
            name=data.name,
            email=data.email,
            password_hash=hash_password(plain_password),
            role_id=role.id,
            must_change_password=True,   # staff must change temp password on first login
        )

        # Fire-and-forget via Celery — non-blocking so the API responds instantly
        send_staff_welcome_email.delay(
            to_email=data.email,
            name=data.name,
            role=data.role,
            temp_password=plain_password,
        )

        logger.info("Staff created: %s (%s)", user.email, data.role)
        return _to_staff_response(user)

    async def get_staff(self, user_id: int) -> StaffResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.role.name not in STAFF_ROLES:
            raise NotFoundException("Staff", user_id)
        team_id = team_name = None
        if user.team_memberships:
            m = user.team_memberships[0]
            team_id   = m.team_id
            team_name = m.team.name if m.team else None
        return _to_staff_response(user, team_id, team_name)

    async def list_staff(self) -> list[StaffResponse]:
        users = await self.user_repo.get_by_roles(
            [RoleName.SUPPORT_AGENT.value, RoleName.TEAM_LEAD.value]
        )
        result = []
        for u in users:
            team_id = team_name = None
            if u.team_memberships:
                m = u.team_memberships[0]
                team_id   = m.team_id
                team_name = m.team.name if m.team else None
            result.append(_to_staff_response(u, team_id, team_name))
        return result

    # ── Teams ──────────────────────────────────────────────────────────────────

    async def create_team(self, data: CreateTeamRequest) -> TeamDetailResponse:
        lead = await self.user_repo.get_by_id(data.team_lead_id)
        if not lead or lead.role.name != RoleName.TEAM_LEAD.value:
            raise AppException(
                "team_lead_id must reference a TEAM_LEAD user.", status_code=400
            )

        team = await self.team_repo.create(
            name=data.name,
            team_lead_id=data.team_lead_id,
        )

        # Add lead as a member so their team_id resolves in the JWT
        await self.team_repo.add_member(team.id, data.team_lead_id)

        # Validate and add agents
        for agent_id in data.agent_ids:
            agent = await self.user_repo.get_by_id(agent_id)
            if not agent or agent.role.name != RoleName.SUPPORT_AGENT.value:
                raise AppException(
                    f"User {agent_id} is not a support agent.", status_code=400
                )
            await self.team_repo.add_member(team.id, agent_id)

        team = await self.team_repo.get_by_id(team.id)
        logger.info("Team created: %s (id=%s)", team.name, team.id)
        return _to_team_detail(team)

    async def get_team(self, team_id: int) -> TeamDetailResponse:
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise NotFoundException("Team", team_id)
        return _to_team_detail(team)

    async def list_teams(self) -> list[TeamDetailResponse]:
        teams = await self.team_repo.get_all()
        return [_to_team_detail(t) for t in teams]

    async def update_team(
        self, team_id: int, data: UpdateTeamRequest
    ) -> TeamDetailResponse:
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise NotFoundException("Team", team_id)

        if data.name is not None:
            team = await self.team_repo.update(team, name=data.name)

        if data.team_lead_id is not None:
            lead = await self.user_repo.get_by_id(data.team_lead_id)
            if not lead or lead.role.name != RoleName.TEAM_LEAD.value:
                raise AppException(
                    "team_lead_id must reference a TEAM_LEAD user.", status_code=400
                )
            team = await self.team_repo.update(team, team_lead_id=data.team_lead_id)
            await self.team_repo.add_member(team.id, data.team_lead_id)

        for agent_id in (data.add_agent_ids or []):
            agent = await self.user_repo.get_by_id(agent_id)
            if not agent or agent.role.name != RoleName.SUPPORT_AGENT.value:
                raise AppException(
                    f"User {agent_id} is not a support agent.", status_code=400
                )
            await self.team_repo.add_member(team.id, agent_id)

        for agent_id in (data.remove_agent_ids or []):
            # Prevent removing the current team lead from the members list
            if agent_id == team.team_lead_id:
                raise AppException(
                    "Cannot remove the team lead from the team members list.",
                    status_code=400,
                )
            await self.team_repo.remove_member(team.id, agent_id)

        team = await self.team_repo.get_by_id(team_id)
        return _to_team_detail(team)

    async def delete_team(self, team_id: int) -> None:
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise NotFoundException("Team", team_id)
        await self.team_repo.delete(team)
        logger.info("Team deleted: id=%s", team_id)

    async def list_teams_dropdown(self) -> list[dict]:
        rows = await self.team_repo.get_all_dropdown()
        return [
            {"id": r.id, "name": r.name, "team_lead_id": r.team_lead_id}
            for r in rows
        ]