"""JWT token creation and decoding utilities."""

import logging
from datetime import datetime, timedelta, timezone
import uuid

from jose import JWTError, jwt
from src.utils.auth_utils import get_current_time
from src.config.settings import settings
from src.core.exceptions.auth_exceptions import InvalidTokenException, TokenExpiredException

logger = logging.getLogger(__name__)


def create_access_token(user_id: int | str,user_email:str, role: str,customer_tier:str,team_id:int) -> str:
    """Create a short-lived JWT access token."""
    expire = get_current_time() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),   # always stringify — int PKs become "1", "2", etc.
        "email":user_email,
        "role": role,
        "customer_tier":customer_tier,
        "team_id":team_id,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id, user_email, role, customer_tier, team_id) -> tuple[str, str, datetime]:
    """Returns (token, jti, expiry)."""
    jti = str(uuid.uuid4())
    expire = get_current_time() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "email": user_email,
        "role": role,
        "customer_tier": customer_tier,
        "team_id": team_id,
        "exp": expire,
        "type": "refresh",
        "jti": jti,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expire


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Logs the real jose error to the terminal so you can see exactly what went wrong.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT decode failed: token has expired")
        raise TokenExpiredException()
    except JWTError as e:
        # This prints the REAL reason (e.g. "Signature verification failed") in the terminal
        logger.warning(f"JWT decode failed: {e} | token_start={token[:30]}...")
        raise InvalidTokenException()