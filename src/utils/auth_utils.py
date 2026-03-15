"""Shared auth utilities: cookie helpers, time helper."""

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


def delete_refresh_cookie(response: Response) -> None:
    """
    Clear the refresh token cookie.

    The attributes (httponly, secure, samesite) MUST match those used in
    set_refresh_cookie — browsers treat them as part of the cookie identity.
    A mismatched delete_cookie call is silently ignored by the browser,
    leaving the original cookie intact.
    """
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="none",
    )


def get_current_time() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)