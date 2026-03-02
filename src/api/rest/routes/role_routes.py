"""Role routes: list available roles."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import require_role
from src.core.services.role_service import RoleService
from src.data.clients.postgres_client import get_db
from src.schemas.role_schema import RoleResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RoleResponse])
async def list_roles(
    current_user: dict = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """List all roles. Admin only."""
    service = RoleService(db)
    return await service.get_all_roles()
