"""JWT token creation and decoding utilities."""

import logging
import uuid
from datetime import datetime, timedelta

from jose import JWTError, jwt

from src.config.settings import settings
from src.core.exceptions.auth_exceptions import InvalidTokenException, TokenExpiredException
from src.utils.auth_utils import get_current_time

logger = logging.getLogger(__name__)


def create_access_token(
    user_id: int | str,
    user_email: str,
    role: str,
    customer_tier: str | None,
    team_id: int | None,
    org_id: int | None = None,
    must_change_password: bool = False,
) -> str:
    """Create a short-lived JWT access token.

    must_change_password is embedded in the ACCESS token so the frontend
    can gate the change-password screen, and so that /auth/refresh always
    returns the current flag value (re-read fresh from DB on every refresh).
    """
    expire = get_current_time() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub":                  str(user_id),
        "email":                user_email,
        "role":                 role,
        "customer_tier":        customer_tier,
        "team_id":              team_id,
        "org_id":               org_id,
        "must_change_password": must_change_password,
        "exp":                  expire,
        "type":                 "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: int | str,
    user_email: str,
    role: str,
    customer_tier: str | None,
    team_id: int | None,
    org_id: int | None = None,
) -> tuple[str, str, datetime]:
    """Create a long-lived refresh token. Returns (token, jti, expiry).

    must_change_password is intentionally NOT stored here — it must always be
    re-read from the DB when issuing a new access token so that a password
    change is reflected on the very next refresh.
    """
    jti    = str(uuid.uuid4())
    expire = get_current_time() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub":           str(user_id),
        "email":         user_email,
        "role":          role,
        "customer_tier": customer_tier,
        "team_id":       team_id,
        "org_id":        org_id,
        "exp":           expire,
        "type":          "refresh",
        "jti":           jti,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expire


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        logger.warning("JWT decode failed: token has expired")
        raise TokenExpiredException()
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e} | token_start={token[:30]}...")
        raise InvalidTokenException()