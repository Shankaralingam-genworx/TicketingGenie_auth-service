"""Request/response logging middleware — logs to terminal."""

import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.observability.logging.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs each request with method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        logger.info(
            f"[{request_id}] --> {request.method} {request.url.path}"
            + (f"?{request.url.query}" if request.url.query else "")
        )

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"[{request_id}] <-- {request.method} {request.url.path} "
            f"| status={response.status_code} | {duration_ms:.1f}ms"
        )

        return response


def add_logging_middleware(app: FastAPI) -> None:
    """Attach logging middleware to the FastAPI app."""
    app.add_middleware(LoggingMiddleware)
