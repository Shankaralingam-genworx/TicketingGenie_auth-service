"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from src.api.middleware.cors import add_cors_middleware
from src.api.middleware.error_handler import add_error_handlers
from src.api.middleware.logging import add_logging_middleware
from src.api.rest.routes import auth_routes, health_routes, role_routes, user_routes,admin_routes,team_routes
from src.api.rest.routes.user_lookup_routes import router as user_lookup_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Ticketing Genie – Auth Service welcome"
    )

    # Middleware (order matters: logging wraps everything)
    add_logging_middleware(app)
    add_cors_middleware(app)
    add_error_handlers(app)

    # Routes
    app.include_router(health_routes.router)
    app.include_router(auth_routes.router, prefix="/api/v1")
    app.include_router(user_routes.router, prefix="/api/v1")
    app.include_router(role_routes.router, prefix="/api/v1")
    app.include_router(admin_routes.router, prefix="/api/v1")
    app.include_router(team_routes.router, prefix="/api/v1")
    
    app.include_router(user_lookup_router, prefix="/api/v1")

    # Override OpenAPI schema to use HTTP Bearer (shows clean token input in Swagger)
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Define a clean bearerAuth security scheme
        schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Paste your access_token here (without 'Bearer ' prefix)",
            }
        }

        # Apply it globally to all endpoints
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                operation["security"] = [{"bearerAuth": []}]

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app