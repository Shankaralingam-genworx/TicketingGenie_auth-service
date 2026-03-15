"""
GET /users/by-email  — internal endpoint for the ticket service.

Ticket service calls this to resolve a user's role and customer tier
by email address (e.g. when processing an inbound email ticket).
No auth header required — both services are on the same internal network.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.postgres_client import get_db
from src.data.repositories.user_repository import UserRepository

router = APIRouter(tags=["Internal — User Lookup"])


class UserLookupResponse(BaseModel):
    id:            int
    email:         str
    role:          str
    customer_tier: str | None = None   # tier name string (e.g. "smb", "enterprise")
    team_id:       int | None = None
    org_id:        int | None = None

    model_config = {"from_attributes": True}


@router.get(
    "/users/by-email",
    response_model=UserLookupResponse,
    summary="Look up a user by email address (internal service use only)",
)
async def get_user_by_email(
    email: str = Query(..., description="Exact email address to look up"),
    db:    AsyncSession = Depends(get_db),
) -> UserLookupResponse:
    """
    Returns the user record for the given email.
    Called service-to-service from ticket-service.

    - **200** — user found
    - **404** — no user with that email
    """
    repo = UserRepository(db)
    user = await repo.get_by_email(email.lower().strip())

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"No user found with email '{email}'",
        )

    role_name     = user.role.name
    customer_tier = None
    team_id       = None

    if role_name == "customer" and user.customer:
        # Return the tier name string so the ticket service can use it directly
        customer_tier = user.customer.tier.name if user.customer.tier else None

    elif role_name in ("support_agent", "team_lead"):
        team_id = user.led_teams[0].id if user.led_teams else None

    return UserLookupResponse(
        id=user.id,
        email=user.email,
        role=role_name,
        customer_tier=customer_tier,
        team_id=team_id,
        org_id=user.org_id,
    )