"""Health check route."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.data.clients.postgres_client import AsyncSessionLocal

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Verifies that the service is running AND that the database is reachable.
    Returns 200 when healthy, 503 when the DB cannot be reached.
    Used by load balancers, container orchestration liveness/readiness probes,
    and monitoring systems.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "service": "ticketing-auth-service"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "service": "ticketing-auth-service",
                "detail": "Database unreachable",
            },
        )