"""
init_db.py — Database initializer for Ticketing Genie Auth Service
"""

import asyncio
from typing import Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.postgres_client import AsyncSessionLocal, create_tables
from src.data.models.postgres.customer_tier_model import CustomerTier
from src.data.models.postgres.role_model import Role
from src.data.models.postgres.user_model import User
from src.observability.logging.logger import get_logger, setup_logging
from src.utils.auth_utils import get_current_time
from src.utils.password_utils import hash_password

setup_logging()
logger = get_logger("init_db")

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

ROLES = ["customer", "support_agent", "team_lead", "admin", "org_admin"]

TIERS = [
    {"name": "smb", "description": "Small and medium-sized business"},
    {"name": "enterprise", "description": "Enterprise-level organisation"},
]

USERS = [
    {
        "name": "Super Admin",
        "email": "admin@ticketinggenie.com",
        "password": "Admin@123",
        "role": "admin",
    },
    {
        "name": "Lead Shankar",
        "email": "shankar077123@gmail.com",
        "password": "Shankar@123",
        "role": "team_lead",
    },
    {
        "name": "Bob Martinez",
        "email": "bob.teamlead@ticketinggenie.com",
        "password": "TeamLead@123",
        "role": "team_lead",
    },
    {
        "name": "Agent Shankar",
        "email": "shankaralingams2004@gmail.com",
        "password": "Shankar@123",
        "role": "support_agent",
    },
    {
        "name": "Agent Kishore",
        "email": "kishoreshankar870@gmail.com",
        "password": "Shankar@123",
        "role": "support_agent",
    },
]

# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


async def seed_roles(db: AsyncSession) -> Dict[str, int]:
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


async def seed_tiers(db: AsyncSession) -> None:
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


async def seed_users(db: AsyncSession, role_map: Dict[str, int]) -> None:
    for data in USERS:
        result = await db.execute(select(User).where(User.email == data["email"]))
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"[=] User exists  : {data['email']}")
            continue

        user = User(
            name=data["name"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
            role_id=role_map[data["role"]],
            is_active=True,
            must_change_password=True,  #  force reset in real systems
            created_at=get_current_time(),
        )

        db.add(user)
        await db.flush()

        logger.info(
            f"[+] {data['role']:<15} created: {data['name']:<20} "
            f"<{data['email']}> id={user.id}"
        )


# ---------------------------------------------------------------------------
# Main reusable initializer
# ---------------------------------------------------------------------------


async def init_database() -> None:
    """Initialize DB (tables + seed data). Safe + reusable."""
    logger.info("=" * 60)
    logger.info("Initializing database...")
    logger.info("=" * 60)

    try:
        await create_tables()
        logger.info("Tables created/verified.")

        async with AsyncSessionLocal() as db:
            role_map = await seed_roles(db)
            await db.flush()

            await seed_tiers(db)
            await db.flush()

            await seed_users(db, role_map)
            await db.flush()

            await db.commit()

        logger.info("Database initialization complete.")

    except Exception as e:
        logger.exception("Database initialization FAILED ❌")
        raise


# ---------------------------------------------------------------------------
# Script entry
# ---------------------------------------------------------------------------


async def main() -> None:
    await init_database()

    logger.info("")
    logger.info("Seed credentials:")
    logger.info("  Admin         : admin@ticketinggenie.com / Admin@123")
    logger.info("  Team Lead     : shankar077123@gmail.com  / Shankar@123")
    logger.info("  Support Agent : shankaralingams2004@gmail.com / Shankar@123")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())