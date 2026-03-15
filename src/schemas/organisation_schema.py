"""Pydantic schemas for organisation endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from src.constants.customer_constants import PreferredContact
from src.schemas.customer_tier_schema import CustomerTierResponse


# ── Organisation CRUD (system admin) ──────────────────────────────────────────

class OrganisationCreate(BaseModel):
    """System admin creates an org and its org_admin in one call."""
    name:             str
    domain:           str | None = None
    customer_tier_id: int | None = None
    # org_admin account details
    admin_name:  str
    admin_email: EmailStr

    @field_validator("name", "admin_name")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be blank.")
        return v


class OrganisationUpdate(BaseModel):
    name:             str | None  = None
    domain:           str | None  = None
    customer_tier_id: int | None  = None
    is_active:        bool | None = None


class OrganisationResponse(BaseModel):
    id:               int
    name:             str
    domain:           str | None
    customer_tier_id: int | None
    tier:             CustomerTierResponse | None
    is_active:        bool
    created_at:       datetime

    model_config = {"from_attributes": True}


class OrganisationCreatedResponse(BaseModel):
    """Returned to the system admin after creating an org + org_admin."""
    organisation:    OrganisationResponse
    org_admin_email: str
    message:         str


# ── Customer management (org_admin) ───────────────────────────────────────────

class OrgCustomerCreate(BaseModel):
    """
    org_admin adds a customer user to their organisation.

    The customer tier is always inherited from the organisation — it is
    not set per-customer.
    """
    name:              str
    email:             EmailStr
    phone:             str | None        = None
    # Using the enum gives Pydantic validation — rejects invalid values at the
    # schema layer with a clear 422 instead of an opaque DB error.
    preferred_contact: PreferredContact  = PreferredContact.EMAIL

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank.")
        return v


class OrgCustomerResponse(BaseModel):
    id:                   int
    name:                 str
    email:                str
    is_active:            bool
    must_change_password: bool
    org_id:               int | None     # nullable — safe for edge cases
    created_at:           datetime
    # customer profile fields
    phone:                str | None     = None
    preferred_contact:    str | None     = None
    customer_tier_id:     int | None     = None
    tier_name:            str | None     = None

    model_config = {"from_attributes": True}