"""Global exception handler middleware."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions.base_exception import AppException
from src.observability.logging.logger import get_logger

logger = get_logger(__name__)


def add_error_handlers(app: FastAPI) -> None:
    """Register global error handlers."""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        """Handle all custom application exceptions."""
        logger.warning(
            f"AppException: {exc.message} | path={request.url.path} | status={exc.status_code}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception):
        """Catch-all for unexpected errors."""
        logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )
