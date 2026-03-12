"""
GET /users/by-email  — internal endpoint for the ticket service.

File path (auth service): src/api/rest/routes/user_lookup_routes.py

Register in app.py:
    from src.api.rest.routes.user_lookup_routes import router as user_lookup_router
    app.include_router(user_lookup_router, prefix="/api/v1")
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.postgres_client import get_db
from src.data.repositories.user_repository import UserRepository

router = APIRouter(tags=["Internal — User Lookup"])


# ── Response schema ───────────────────────────────────────────────────────────

class UserLookupResponse(BaseModel):
    id:            int
    email:         str
    role:          str
    customer_tier: str | None = None
    team_id:       int | None = None

    model_config = {"from_attributes": True}


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get(
    "/users/by-email",
    response_model = UserLookupResponse,
    summary        = "Look up a user by email address (internal service use only)",
)
async def get_user_by_email(
    email: str = Query(..., description="Exact email address to look up"),
    db:    AsyncSession = Depends(get_db),
) -> UserLookupResponse:
    """
    Returns the user record for the given email.
    Called service-to-service from ticket-service — no auth header needed
    since both services are on the same internal Docker network.

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

    if role_name == "customer":
        customer_tier = (
            user.customer.customer_tier
            if user.customer and user.customer.customer_tier
            else None
        )
    elif role_name in ("support_agent", "team_lead"):
        team_id = user.led_teams[0].id if user.led_teams else None

    return UserLookupResponse(
        id            = user.id,
        email         = user.email,
        role          = role_name,
        # customer_tier is an Enum — extract .value ("ENTERPRISE") then lowercase → "enterprise"
        customer_tier = (customer_tier.value if hasattr(customer_tier, "value") else str(customer_tier)).lower() if customer_tier else None,
        team_id       = team_id,
    )