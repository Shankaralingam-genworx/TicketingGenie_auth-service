"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.exceptions.auth_exceptions import ForbiddenException, UnauthorizedException
from src.core.security import decode_token

# Bearer token extractor
bearer_scheme = HTTPBearer()

# The only endpoint a user with must_change_password=True may call.
# Everything else is blocked until the password is changed.
_CHANGE_PASSWORD_PATH_SUFFIX = "/me/change-password"


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Decode and validate the JWT access token from the Authorization header.
    Returns the token payload dict.

    Also enforces must_change_password server-side: if the flag is True the
    user may only reach POST /users/me/change-password — all other endpoints
    return 403.  This prevents a user with a temporary password from calling
    any API endpoint directly, bypassing the frontend guard.
    """
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise UnauthorizedException("Invalid or expired access token")

    if payload.get("type") != "access":
        raise UnauthorizedException("Not an access token")

    # Validate sub claim is present and is a valid integer string
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedException("Invalid token: missing subject claim.")
    try:
        int(sub)
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid token: malformed subject claim.")

    # Server-side enforcement of the forced password-change gate.
    # The frontend enforces this too, but a direct API caller must also be blocked.
    if payload.get("must_change_password"):
        if not request.url.path.endswith(_CHANGE_PASSWORD_PATH_SUFFIX):
            raise ForbiddenException(
                "You must change your password before accessing this resource."
            )

    return payload


def require_role(*roles: str):
    """
    Dependency factory that enforces role-based access control.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    or:
        @router.get("/admin")
        async def endpoint(user=Depends(require_role("admin", "team_lead"))):
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