"""Application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.observability.logging.logger import get_logger, setup_logging
from src.api.rest.app import create_app
from src.init_db import init_database         

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting Ticketing Genie Auth Service...")

    await init_database()                    

    logger.info("Auth Service is ready at http://localhost:8001")
    logger.info("API docs available at http://localhost:8001/docs")

    yield

    logger.info("Auth Service shutting down.")


app: FastAPI = create_app()
app.router.lifespan_context = lifespan