"""Health check route."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.data.clients.postgres_client import AsyncSessionLocal

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "service": "ticketing-auth-service"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "service": "ticketing-auth-service",
                "detail": "Database unreachable",
            },
        )