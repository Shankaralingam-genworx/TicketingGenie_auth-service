"""Application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.core.services.role_service import RoleService
from src.core.services.customer_tier_service import CustomerTierService
from src.schemas.customer_tier_schema import CustomerTierCreate
from src.data.clients.postgres_client import AsyncSessionLocal, create_tables
from src.observability.logging.logger import get_logger, setup_logging
from src.api.rest.app import create_app

setup_logging()
logger = get_logger(__name__)

# ── Seed data ─────────────────────────────────────────────────────────────────
# These are seeded once on startup and never overwritten.

# Additional roles that live only in the DB (not in the RoleName enum).
# The four built-in roles (admin, support_agent, team_lead, customer) are
# seeded by role_service.seed_roles() via the RoleName enum.
EXTRA_ROLES = ["org_admin"]

# Default customer tiers.  Add more here if needed.
DEFAULT_TIERS = [
    CustomerTierCreate(name="smb",        description="Small and medium-sized business"),
    CustomerTierCreate(name="enterprise", description="Enterprise-level organisation"),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting Ticketing Genie Auth Service...")

    # Create all DB tables (SQLAlchemy metadata — no Alembic)
    await create_tables()
    logger.info("Database tables created/verified.")

    async with AsyncSessionLocal() as session:
        role_service = RoleService(session)

        # Seed the four built-in roles from the RoleName enum
        await role_service.seed_roles()

        # Seed extra DB-only roles (e.g. org_admin) that are not in the enum
        for role_name in EXTRA_ROLES:
            existing = await role_service.get_role_by_name(role_name)
            if not existing:
                await role_service.create_role(role_name)
                logger.info(f"Seeded extra role: '{role_name}'")

        await session.commit()
        logger.info("Roles seeded.")

        # Seed default customer tiers (idempotent — skips existing names)
        tier_service = CustomerTierService(session)
        for tier in DEFAULT_TIERS:
            existing = await tier_service.repo.get_by_name(tier.name)
            if not existing:
                await tier_service.repo.create(
                    name=tier.name, description=tier.description
                )
                logger.info(f"Seeded customer tier: '{tier.name}'")

        await session.commit()
        logger.info("Customer tiers seeded.")

    logger.info("Auth Service is ready at http://localhost:8001")
    logger.info("API docs available at http://localhost:8001/docs")

    yield

    logger.info("Auth Service shutting down.")


app = create_app()
app.router.lifespan_context = lifespan