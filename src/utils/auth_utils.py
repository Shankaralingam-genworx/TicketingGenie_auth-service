"""Shared auth utilities: cookie helper."""

from datetime import datetime, timezone

from fastapi import Response


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Attach the refresh token as an httpOnly cookie."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
    )


def get_current_time() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)