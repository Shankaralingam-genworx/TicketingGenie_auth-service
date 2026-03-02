"""
init_db.py — Database initializer for Ticketing Genie Auth Service

Seeds:
  - 4 Roles  (CUSTOMER, SUPPORT_AGENT, TEAM_LEAD, ADMIN)
  - 1 Admin
  - 2 Team Leads
  - 5 Support Agents

Works with int auto-increment primary keys on all tables.

Run:
    python init_db.py
Or via Docker:
    docker-compose exec auth-service python init_db.py
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.postgres_client import AsyncSessionLocal, create_tables
from src.data.models.postgres.role_model import Role
from src.data.models.postgres.user_model import User
from src.observability.logging.logger import get_logger, setup_logging
from src.utils.password_utils import hash_password

setup_logging()
logger = get_logger("init_db")

# ---------------------------------------------------------------------------
# Seed Data — change passwords before going to production!
# ---------------------------------------------------------------------------

ROLES = ["CUSTOMER", "SUPPORT_AGENT", "TEAM_LEAD", "ADMIN"]

USERS = [
    # 1 Admin
    {
        "name": "Super Admin",
        "email": "admin@ticketinggenie.com",
        "password": "Admin@1234",
        "role": "ADMIN",
    },
    # 2 Team Leads
    {
        "name": "Alice Johnson",
        "email": "alice.teamlead@ticketinggenie.com",
        "password": "TeamLead@1234",
        "role": "TEAM_LEAD",
    },
    {
        "name": "Bob Martinez",
        "email": "bob.teamlead@ticketinggenie.com",
        "password": "TeamLead@1234",
        "role": "TEAM_LEAD",
    },
    # 5 Support Agents
    {
        "name": "Charlie Davis",
        "email": "charlie.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "SUPPORT_AGENT",
    },
    {
        "name": "Diana Lee",
        "email": "diana.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "SUPPORT_AGENT",
    },
    {
        "name": "Ethan Brown",
        "email": "ethan.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "SUPPORT_AGENT",
    },
    {
        "name": "Fiona Clark",
        "email": "fiona.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "SUPPORT_AGENT",
    },
    {
        "name": "George Wilson",
        "email": "george.agent@ticketinggenie.com",
        "password": "Agent@1234",
        "role": "SUPPORT_AGENT",
    },
]

# ---------------------------------------------------------------------------
# Seed Functions
# ---------------------------------------------------------------------------


async def seed_roles(db: AsyncSession) -> dict[str, int]:
    """Create roles if they don't exist. Returns role_name → role_id (int) map."""
    role_map: dict[str, int] = {}

    for name in ROLES:
        result = await db.execute(select(Role).where(Role.name == name))
        role = result.scalar_one_or_none()

        if not role:
            role = Role(name=name)
            db.add(role)
            await db.flush()  # flush so the DB assigns the auto-increment id
            logger.info(f"  [+] Role created : {name:<15} id={role.id}")
        else:
            logger.info(f"  [=] Role exists  : {name:<15} id={role.id}")

        role_map[name] = role.id

    return role_map


async def seed_users(db: AsyncSession, role_map: dict[str, int]) -> None:
    """Create seed users if they don't already exist."""
    for data in USERS:
        result = await db.execute(select(User).where(User.email == data["email"]))
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"  [=] User exists  : {data['email']}")
            continue

        user = User(
            name=data["name"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
            role_id=role_map[data["role"]],   # int FK
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()  # flush to get auto-increment user id
        logger.info(
            f"  [+] {data['role']:<15} created: {data['name']:<20} "
            f"<{data['email']}> id={user.id}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    logger.info("=" * 60)
    logger.info("Ticketing Genie — Database Initializer")
    logger.info("=" * 60)

    logger.info("\n[1/3] Creating database tables (if not exist)...")
    await create_tables()
    logger.info("      Tables OK.")

    async with AsyncSessionLocal() as db:
        logger.info("\n[2/3] Seeding roles...")
        role_map = await seed_roles(db)

        logger.info("\n[3/3] Seeding users...")
        await seed_users(db, role_map)

        await db.commit()

    logger.info("\n" + "=" * 60)
    logger.info("Initialization complete! Seeded credentials:")
    logger.info("=" * 60)
    logger.info("  ADMIN")
    logger.info("    admin@ticketinggenie.com          | Admin@1234")
    logger.info("")
    logger.info("  TEAM LEAD")
    logger.info("    alice.teamlead@ticketinggenie.com | TeamLead@1234")
    logger.info("    bob.teamlead@ticketinggenie.com   | TeamLead@1234")
    logger.info("")
    logger.info("  SUPPORT AGENT")
    logger.info("    charlie.agent@ticketinggenie.com  | Agent@1234")
    logger.info("    diana.agent@ticketinggenie.com    | Agent@1234")
    logger.info("    ethan.agent@ticketinggenie.com    | Agent@1234")
    logger.info("    fiona.agent@ticketinggenie.com    | Agent@1234")
    logger.info("    george.agent@ticketinggenie.com   | Agent@1234")
    logger.info("")
    logger.info("  Tip: Change all passwords before going to production!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())