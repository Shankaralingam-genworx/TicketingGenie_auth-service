"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.services.role_service import RoleService
from src.data.clients.postgres_client import AsyncSessionLocal, create_tables
from src.observability.logging.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting Ticketing Genie Auth Service...")

    # Create DB tables (no alembic — direct table creation)
    await create_tables()
    logger.info("Database tables created/verified.")

    # Seed default roles
    async with AsyncSessionLocal() as session:
        role_service = RoleService(session)
        await role_service.seed_roles()
        await session.commit()
    logger.info("Default roles seeded.")

    logger.info("Auth Service is ready at http://0.0.0.0:8000")
    logger.info("API docs available at http://0.0.0.0:8000/docs")
    yield
    logger.info("Auth Service shutting down.")


# Import here to avoid circular imports at module level
from src.api.rest.app import create_app  # noqa: E402

app = create_app()
app.router.lifespan_context = lifespan

