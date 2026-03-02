"""CORS middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors_middleware(app: FastAPI) -> None:
    """Attach CORS middleware to the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Restrict in production to specific domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
