"""Entry point for the Auth Service."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.observability.logging.logger import setup_logging, get_logger
from src.init_db import init_database


setup_logging()
logger = get_logger(__name__).bind(service="auth-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("service_starting")

    # Initialize DB
    await init_database()

    logger.info("service_ready", docs_url="/docs")
    yield

    logger.info("service_stopping")



from src.api.rest.app import create_app  # noqa: E402

app: FastAPI = create_app()
app.router.lifespan_context = lifespan


if __name__ == "__main__":
    from src.config.settings import settings

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
        log_config=None,  
    )