"""Customer tier routes — admin manages tiers via these endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import require_role
from src.core.services.customer_tier_service import CustomerTierService
from src.data.clients.postgres_client import get_db
from src.schemas.customer_tier_schema import (
    CustomerTierCreate,
    CustomerTierResponse,
    CustomerTierUpdate,
)

router = APIRouter(prefix="/customer-tiers", tags=["Customer Tiers"])


@router.get("/", response_model=list[CustomerTierResponse])
async def list_tiers(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all customer tiers. Admin only."""
    return await CustomerTierService(db).get_all()


@router.post(
    "/",
    response_model=CustomerTierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tier(
    payload: CustomerTierCreate,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new customer tier. Admin only."""
    return await CustomerTierService(db).create(payload)


@router.patch("/{tier_id}", response_model=CustomerTierResponse)
async def update_tier(
    tier_id: int,
    payload: CustomerTierUpdate,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update a customer tier (rename / toggle active). Admin only."""
    return await CustomerTierService(db).update(tier_id, payload)


@router.delete("/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tier(
    tier_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a customer tier. Admin only.
    Blocked if any customers are currently assigned this tier.
    """
    await CustomerTierService(db).delete(tier_id)