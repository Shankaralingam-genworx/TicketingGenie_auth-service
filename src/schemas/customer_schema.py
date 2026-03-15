"""Pydantic schemas for customer profile."""

from datetime import datetime

from pydantic import BaseModel

from src.constants.customer_constants import PreferredContact
from src.schemas.customer_tier_schema import CustomerTierResponse


class CustomerProfileResponse(BaseModel):
    id:               int
    user_id:          int
    org_id:           int | None          # nullable — customers without an org are valid
    phone:            str | None
    preferred_contact: PreferredContact | None
    customer_tier_id: int | None
    tier:             CustomerTierResponse | None = None

    model_config = {"from_attributes": True}


class CurrentUserResponse(BaseModel):
    """Full profile returned by GET /users/me for any role."""
    id:                   int
    name:                 str
    email:                str
    role:                 str
    is_active:            bool
    must_change_password: bool
    org_id:               int | None
    org_name:             str | None
    created_at:           datetime
    customer_profile:     CustomerProfileResponse | None = None

    model_config = {"from_attributes": True}