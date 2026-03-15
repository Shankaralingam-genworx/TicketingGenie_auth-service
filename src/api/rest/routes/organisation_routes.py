"""Organisation routes.

System admin (role=admin):
  POST  /organisations/            Create org + org_admin account
  GET   /organisations/            List all organisations
  GET   /organisations/{id}        Get single organisation
  PATCH /organisations/{id}        Update organisation details

org_admin (role=org_admin):
  GET   /organisations/me                              View own org
  GET   /organisations/me/customers                   List customers in own org
  POST  /organisations/me/customers                   Add a customer to own org
  PATCH /organisations/me/customers/{uid}/deactivate  Deactivate a customer
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import require_role
from src.core.services.organisation_service import OrganisationService
from src.data.clients.postgres_client import get_db
from src.schemas.organisation_schema import (
    OrgCustomerCreate,
    OrgCustomerResponse,
    OrganisationCreate,
    OrganisationCreatedResponse,
    OrganisationResponse,
    OrganisationUpdate,
)

router = APIRouter(prefix="/organisations", tags=["Organisations"])


# ── org_admin: self-service portal ────────────────────────────────────────────

@router.get(
    "/me",
    response_model=OrganisationResponse,
    summary="org_admin: view own organisation",
)
async def get_my_organisation(
    current_user: dict = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db),
):
    org_id = _get_org_id(current_user)
    return await OrganisationService(db).get_my_organisation(org_id)


@router.get(
    "/me/customers",
    response_model=list[OrgCustomerResponse],
    summary="org_admin: list all customers in own organisation",
)
async def list_org_customers(
    current_user: dict = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db),
):
    org_id = _get_org_id(current_user)
    return await OrganisationService(db).list_org_customers(org_id)


@router.post(
    "/me/customers",
    response_model=OrgCustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="org_admin: add a customer user to own organisation",
)
async def add_customer(
    payload: OrgCustomerCreate,
    current_user: dict = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a customer user + customer profile.

    Customer tier is automatically inherited from the organisation.
    Temporary password is generated and emailed to the new customer.
    Customer must change password on first login.
    """
    org_id = _get_org_id(current_user)
    return await OrganisationService(db).add_customer(org_id, payload)


@router.patch(
    "/me/customers/{customer_user_id}/deactivate",
    response_model=OrgCustomerResponse,
    summary="org_admin: deactivate a customer in own organisation",
)
async def deactivate_customer(
    customer_user_id: int,
    current_user: dict = Depends(require_role("org_admin")),
    db: AsyncSession = Depends(get_db),
):
    org_id = _get_org_id(current_user)
    return await OrganisationService(db).deactivate_customer(org_id, customer_user_id)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _get_org_id(current_user: dict) -> int:
    """Extract org_id from JWT claims; raise 403 if missing."""
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organisation associated with this account.",
        )
    return int(org_id)


# ── System admin: Organisation CRUD ───────────────────────────────────────────

@router.get(
    "/",
    response_model=list[OrganisationResponse],
    summary="List all organisations (admin only)",
)
async def list_organisations(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OrganisationService(db).list_organisations()


@router.post(
    "/",
    response_model=OrganisationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organisation + org_admin account (admin only)",
)
async def create_organisation(
    data: OrganisationCreate,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Atomically creates:
    1. The Organisation record
    2. An org_admin user with a temporary password

    The temporary password is emailed to admin_email.
    The org_admin must change their password on first login.
    """
    return await OrganisationService(db).create_organisation(data)


@router.get(
    "/{org_id}",
    response_model=OrganisationResponse,
    summary="Get a single organisation (admin only)",
)
async def get_organisation(
    org_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OrganisationService(db).get_organisation(org_id)


@router.patch(
    "/{org_id}",
    response_model=OrganisationResponse,
    summary="Update organisation details (admin only)",
)
async def update_organisation(
    org_id: int,
    payload: OrganisationUpdate,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OrganisationService(db).update_organisation(org_id, payload)