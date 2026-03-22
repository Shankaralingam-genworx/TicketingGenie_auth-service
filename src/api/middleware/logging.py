"""Request/response logging middleware — structured + request tracing."""

import time
import uuid

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.observability.logging.logger import get_logger

logger = get_logger(__name__).bind(service="auth-service")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs each request with method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next):
        # Generate request_id
        request_id = str(uuid.uuid4())

        # Bind request_id globally 
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()

        # Request start log
        logger.info(
            "request_start",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query),
        )

        try:
            response = await call_next(request)

        except Exception as e:
            # Error log
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000

        # Request end log
        logger.info(
            "request_end",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Clear context (important for async safety)
        structlog.contextvars.clear_contextvars()

        return response


def add_logging_middleware(app: FastAPI) -> None:
    """Attach logging middleware to the FastAPI app."""
    app.add_middleware(LoggingMiddleware)