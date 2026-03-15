"""Role routes: list, create, update, and delete roles."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import require_role
from src.core.services.role_service import RoleService
from src.data.clients.postgres_client import get_db
from src.schemas.role_schema import RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RoleResponse])
async def list_roles(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all roles. Admin only."""
    service = RoleService(db)
    return await service.get_all_roles()


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new role. Admin only."""
    service = RoleService(db)
    existing = await service.get_role_by_name(payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{payload.name}' already exists.",
        )
    return await service.create_role(payload.name)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    payload: RoleUpdate,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Rename a role. Admin only."""
    service = RoleService(db)
    role = await service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    if payload.name:
        conflict = await service.get_role_by_name(payload.name)
        if conflict and conflict.id != role_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{payload.name}' already exists.",
            )
    return await service.update_role(role_id, payload.name)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a role. Admin only. Cannot delete roles that are in use."""
    service = RoleService(db)
    role = await service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    in_use = await service.is_role_in_use(role_id)
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a role that is assigned to users.",
        )
    await service.delete_role(role_id)