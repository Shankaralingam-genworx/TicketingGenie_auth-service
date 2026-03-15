"""User routes: profile, password change, user listing."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_current_user, require_role
from src.core.exceptions.auth_exceptions import UnauthorizedException
from src.core.services.customer_service import CustomerService
from src.core.services.user_service import UserService
from src.data.clients.postgres_client import get_db
from src.schemas.customer_schema import CurrentUserResponse
from src.schemas.user_schema import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    UserListResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the profile of the currently authenticated user."""
    user_id = current_user.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token: missing subject claim.")
    service = CustomerService(db)
    return await service.get_current_user_profile(user_id)


@router.post("/me/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the authenticated user's password.

    - First-login (must_change_password=True): old_password is not required.
    - Normal change: old_password must be supplied and correct.
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token: missing subject claim.")
    service = UserService(db)
    return await service.change_password(
        user_id=int(user_id),
        new_password=body.new_password,
        old_password=body.old_password,
    )


@router.get("/", response_model=UserListResponse)
async def list_users(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Admin only."""
    service = UserService(db)
    users = await service.list_users()
    return UserListResponse(users=users, total=len(users))