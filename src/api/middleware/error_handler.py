"""Global exception handler middleware."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from src.core.exceptions.base_exception import AppException
from src.observability.logging.logger import get_logger

logger = get_logger(__name__).bind(service="auth-service")


def add_error_handlers(app: FastAPI) -> None:
    """Register global error handlers."""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        """Handle all custom application exceptions."""

        logger.warning(
            "app_exception",
            path=request.url.path,
            method=request.method,
            status_code=exc.status_code,
            message=exc.message,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError):
        """Handle DB constraint violations."""

        logger.warning(
            "db_integrity_error",
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=409,
            content={"detail": "A record with this value already exists."},
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception):
        """Catch-all for unexpected errors."""

        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )