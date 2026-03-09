"""User routes: profile, admin user listing."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_current_user, require_role
from src.core.services.customer_service import CustomerService
from src.core.services.user_service import UserService
from src.data.clients.postgres_client import get_db
from src.schemas.customer_schema import CurrentUserResponse
from src.schemas.user_schema import UserListResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the profile of the currently authenticated user."""
    service = CustomerService(db)
    return await service.get_current_user_profile(current_user["sub"])


@router.get("/", response_model=UserListResponse)
async def list_users(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Admin only."""
    service = UserService(db)
    users = await service.list_users()
    return UserListResponse(users=users, total=len(users))
