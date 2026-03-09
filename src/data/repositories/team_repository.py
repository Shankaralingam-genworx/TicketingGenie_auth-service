"""Team repository."""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.postgres.team_model import Team
from src.data.models.postgres.user_model import User
from src.data.models.postgres.team_member_model import TeamMember


class TeamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _base_query(self):
        return select(Team).options(
            selectinload(Team.team_lead).selectinload(User.role),
            selectinload(Team.members)
            .selectinload(TeamMember.user)
            .selectinload(User.role),
        )

    async def create(self, name: str, team_lead_id: int) -> Team:
        team = Team(name=name, team_lead_id=team_lead_id)
        self.db.add(team)
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def get_by_id(self, team_id: int) -> Team | None:
        result = await self.db.execute(
            self._base_query().where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Team]:
        result = await self.db.execute(self._base_query().order_by(Team.created_at.desc()))
        return list(result.scalars().all())

    async def update(self, team: Team, **kwargs) -> Team:
        for k, v in kwargs.items():
            setattr(team, k, v)
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def delete(self, team: Team) -> None:
        await self.db.delete(team)
        await self.db.flush()

    async def add_member(self, team_id: int, user_id: int) -> None:
        """Add a user to a team. Silently ignores if already a member."""
        existing = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            self.db.add(TeamMember(team_id=team_id, user_id=user_id))
            await self.db.flush()

    async def remove_member(self, team_id: int, user_id: int) -> None:
        await self.db.execute(
            delete(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        await self.db.flush()
        
    async def get_all_dropdown(self) -> list[Team]:
        result = await self.db.execute(
            select(Team.id, Team.name, Team.team_lead_id)
            .order_by(Team.name.asc())
        )
        return result.all()