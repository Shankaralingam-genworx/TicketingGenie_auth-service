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
from src.observability.logging.logger import get_logger
from src.utils.auth_utils import get_current_time
from src.utils.password_utils import hash_password


logger = get_logger("init_db").bind(service="auth-service")

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

    logger.info("seeding_roles_started")
    role_map: Dict[str, int] = {}

    for name in ROLES:
        result = await db.execute(select(Role).where(Role.name == name))
        role = result.scalar_one_or_none()

        if not role:
            role = Role(name=name)
            db.add(role)
            await db.flush()
            logger.info(
                        "role_created",
                        role=name,
                        role_id=role.id,
            )
        else:
            logger.info(
                "role_exists",
                role=name,
                role_id=role.id,
            )

        role_map[name] = role.id

    return role_map


async def seed_tiers(db: AsyncSession) -> None:

    logger.info("seeding_tiers_started")

    for t in TIERS:
        result = await db.execute(
            select(CustomerTier).where(CustomerTier.name == t["name"])
        )
        tier = result.scalar_one_or_none()

        if not tier:
            tier = CustomerTier(name=t["name"], description=t["description"])
            db.add(tier)
            await db.flush()
            logger.info(
                        "tier_created",
                        tier=t["name"],
                        tier_id=tier.id,
            )
        else:
            logger.info(
                "tier_exists",
                tier=t["name"],
                tier_id=tier.id,
            )


async def seed_users(db: AsyncSession, role_map: Dict[str, int]) -> None:

    logger.info("seeding_users_started")

    for data in USERS:
        result = await db.execute(select(User).where(User.email == data["email"]))
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                        "user_exists",
                         user_id=existing.id,
                     )
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
                "user_created",
                user_id=user.id,
                role=data["role"],
            )


# ---------------------------------------------------------------------------
# Main reusable initializer
# ---------------------------------------------------------------------------


async def init_database() -> None:
    """Initialize DB (tables + seed data). Safe + reusable."""

    logger.info("db_init_started")

    try:
        await create_tables()
        logger.info("db_tables_ready")

        async with AsyncSessionLocal() as db:
            role_map = await seed_roles(db)
            await db.flush()

            await seed_tiers(db)
            await db.flush()

            await seed_users(db, role_map)
            await db.flush()

            await db.commit()

        logger.info("db_init_completed")

    except Exception as e:
        logger.exception("db_init_failed", error=str(e))
        raise


# ---------------------------------------------------------------------------
# Script entry
# ---------------------------------------------------------------------------


async def main() -> None:
    await init_database()

if __name__ == "__main__":
    asyncio.run(main())