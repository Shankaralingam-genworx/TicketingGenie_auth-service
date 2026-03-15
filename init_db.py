"""
init_db.py — Database initializer for Ticketing Genie Auth Service

Seeds:
  - Roles         : customer, support_agent, team_lead, admin, org_admin
  - Customer tiers: smb, enterprise
  - Users         : admin, 2 team leads, 5 support agents
  - Teams         : Backend Support Team, Infrastructure Team
  - Organisation  : KCE (domain: kce.ac.in) with its org_admin user

All tables use Integer auto-increment primary keys and Integer foreign keys.
"""

import asyncio
from typing import Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.postgres_client import AsyncSessionLocal, create_tables
from src.data.models.postgres.customer_tier_model import CustomerTier
from src.data.models.postgres.organisation_model import Organisation
from src.data.models.postgres.role_model import Role
from src.data.models.postgres.team_member_model import TeamMember
from src.data.models.postgres.team_model import Team
from src.data.models.postgres.user_model import User
from src.observability.logging.logger import get_logger, setup_logging
from src.utils.auth_utils import get_current_time
from src.utils.password_utils import hash_password

setup_logging()
logger = get_logger("init_db")

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

# Roles — the four built-in roles + org_admin (DB-only role)
ROLES = ["customer", "support_agent", "team_lead", "admin", "org_admin"]

# Customer tiers
TIERS = [
    {"name": "smb",        "description": "Small and medium-sized business"},
    {"name": "enterprise", "description": "Enterprise-level organisation"},
]

# Staff + admin users
USERS = [
    {
        "name": "Super Admin",
        "email": "admin@ticketinggenie.com",
        "password": "Admin@1234",
        "role": "admin",
    },
    {
        "name": "Alice Johnson",
        "email": "alice.teamlead@ticketinggenie.com",
        "password": "TeamLead@1234",
        "role": "team_lead",
    },
    {
        "name": "Bob Martinez",
        "email": "bob.teamlead@ticketinggenie.com",
        "password": "TeamLead@1234",
        "role": "team_lead",
    },
    {
        "name": "Charlie Davis",
        "email": "charlie.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "support_agent",
    },
    {
        "name": "Diana Lee",
        "email": "diana.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "support_agent",
    },
    {
        "name": "Ethan Brown",
        "email": "ethan.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "support_agent",
    },
    {
        "name": "Fiona Clark",
        "email": "fiona.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "support_agent",
    },
    {
        "name": "George Wilson",
        "email": "george.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "support_agent",
    },
]

# Teams
TEAMS = [
    {
        "name": "Backend Support Team",
        "lead_email": "alice.teamlead@ticketinggenie.com",
        "members": [
            "charlie.agent@ticketinggenie.com",
            "diana.agent@ticketinggenie.com",
            "ethan.agent@ticketinggenie.com",
        ],
    },
    {
        "name": "Infrastructure Team",
        "lead_email": "bob.teamlead@ticketinggenie.com",
        "members": [
            "fiona.agent@ticketinggenie.com",
            "george.agent@ticketinggenie.com",
        ],
    },
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


async def seed_roles(db: AsyncSession) -> Dict[str, int]:
    """Create roles if they don't exist. Returns role_name -> role_id map."""
    role_map: Dict[str, int] = {}
    for name in ROLES:
        result = await db.execute(select(Role).where(Role.name == name))
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=name)
            db.add(role)
            await db.flush()
            logger.info(f"[+] Role created : {name:<15} id={role.id}")
        else:
            logger.info(f"[=] Role exists  : {name:<15} id={role.id}")
        role_map[name] = role.id
    return role_map


async def seed_tiers(db: AsyncSession) -> Dict[str, int]:
    """Create customer tiers if they don't exist. Returns name -> id map."""
    tier_map: Dict[str, int] = {}
    for t in TIERS:
        result = await db.execute(
            select(CustomerTier).where(CustomerTier.name == t["name"])
        )
        tier = result.scalar_one_or_none()
        if not tier:
            tier = CustomerTier(name=t["name"], description=t["description"])
            db.add(tier)
            await db.flush()
            logger.info(f"[+] Tier created : {t['name']:<15} id={tier.id}")
        else:
            logger.info(f"[=] Tier exists  : {t['name']:<15} id={tier.id}")
        tier_map[t["name"]] = tier.id
    return tier_map


async def seed_users(db: AsyncSession, role_map: Dict[str, int]) -> None:
    """Create seed staff + admin users if not already present."""
    for data in USERS:
        result = await db.execute(select(User).where(User.email == data["email"]))
        if result.scalar_one_or_none():
            logger.info(f"[=] User exists  : {data['email']}")
            continue

        user = User(
            name=data["name"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
            role_id=role_map[data["role"]],
            is_active=True,
            must_change_password=False,
            created_at=get_current_time(),
        )
        db.add(user)
        await db.flush()
        logger.info(
            f"[+] {data['role']:<15} created: {data['name']:<20} "
            f"<{data['email']}> id={user.id}"
        )


async def seed_teams(db: AsyncSession) -> None:
    """Create teams and assign members."""
    for team_data in TEAMS:
        result = await db.execute(
            select(Team).where(Team.name == team_data["name"])
        )
        if result.scalar_one_or_none():
            logger.info(f"[=] Team exists  : {team_data['name']}")
            continue

        result = await db.execute(
            select(User).where(User.email == team_data["lead_email"])
        )
        team_lead = result.scalar_one()

        team = Team(name=team_data["name"], team_lead_id=team_lead.id)
        db.add(team)
        await db.flush()
        logger.info(f"[+] Team created : {team.name:<25} Lead={team_lead.email}")

        # Add team lead as a member so team_id resolves in JWT
        db.add(TeamMember(team_id=team.id, user_id=team_lead.id))

        for member_email in team_data["members"]:
            result = await db.execute(
                select(User).where(User.email == member_email)
            )
            member = result.scalar_one()
            db.add(TeamMember(team_id=team.id, user_id=member.id))
            logger.info(f"    ↳ Member added: {member.email}")



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    logger.info("=" * 60)
    logger.info("Ticketing Genie — Database Initializer")
    logger.info("=" * 60)

    await create_tables()
    logger.info("Tables created/verified.")

    async with AsyncSessionLocal() as db:
        role_map = await seed_roles(db)
        await db.flush()

        tier_map = await seed_tiers(db)
        await db.flush()

        await seed_users(db, role_map)
        await db.flush()

        await seed_teams(db)
        await db.flush()

        await db.commit()

    logger.info("=" * 60)
    logger.info("Initialization complete!")
    logger.info("")
    logger.info("Seed credentials:")
    logger.info("  Admin         : admin@ticketinggenie.com           / Admin@1234")
    logger.info("  Team Lead     : alice.teamlead@ticketinggenie.com  / TeamLead@1234")
    logger.info("  Support Agent : charlie.agent@ticketinggenie.com   / Agent@1234")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())