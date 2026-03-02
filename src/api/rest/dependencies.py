"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.exceptions.auth_exceptions import ForbiddenException, UnauthorizedException
from src.core.security import decode_token

# Bearer token extractor
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Decode and validate the JWT access token from the Authorization header.
    Returns the token payload dict: { sub, role, exp, type }.
    Raises UnauthorizedException if token is missing or invalid.
    """
    try:
        payload = decode_token(credentials.credentials)
        # print(payload)
    except Exception as e:
        # print("JWT ERROR:", str(e))
        raise UnauthorizedException("Invalid or expired access token")

    if payload.get("type") != "access":
        raise UnauthorizedException("Not an access token")

    return payload


def require_role(*roles: str):
    """
    Dependency factory that enforces role-based access control.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("ADMIN"))])
    or:
        @router.get("/admin")
        async def endpoint(user=Depends(require_role("ADMIN", "TEAM_LEAD"))):
            ...
    """

    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        if user_role not in roles:
            raise ForbiddenException(
                f"Access denied. Required role(s): {', '.join(roles)}"
            )
        return current_user

    return role_checker
