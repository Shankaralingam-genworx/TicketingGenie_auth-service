from fastapi import APIRouter, Depends, Response
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
from src.utils.auth_utils import set_refresh_cookie

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
    return await CustomerService(db).get_current_user_profile(user_id)


@router.post("/me/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    
    user_id = current_user.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token: missing subject claim.")

    change_response, new_refresh_token = await UserService(db).change_password(
        user_id=int(user_id),
        new_password=body.new_password,
        old_password=body.old_password,
    )

    # Set the new refresh token cookie — this replaces the old one in the browser
    set_refresh_cookie(response, new_refresh_token)

    return change_response


@router.get("/", response_model=UserListResponse)
async def list_users(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Admin only."""
    service = UserService(db)
    users = await service.list_users()
    return UserListResponse(users=users, total=len(users))