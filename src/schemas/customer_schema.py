"""Pydantic schemas for customer registration and profile."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator, Field
from src.constants.customer_constants import CustomerTier, PreferredContact


class CustomerRegisterRequest(BaseModel):
    name: str = Field(..., description="Full name of the customer")
    email: EmailStr = Field(..., description="Customer email")
    password: str = Field(..., description="Password, minimum 8 characters")
    phone: str | None = Field(None, description="Optional phone number")
    customer_tier: CustomerTier = Field(
        CustomerTier.BASIC, description="Customer tier: BASIC, PREMIUM, STANDARD"
    )
    preferred_contact: PreferredContact = Field(
        PreferredContact.EMAIL, description="Preferred contact method: EMAIL or WEB"
    )

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class CustomerProfileResponse(BaseModel):
    id: int
    user_id: int
    phone: str | None
    customer_tier: CustomerTier
    preferred_contact: PreferredContact

    model_config = {"from_attributes": True}


class CurrentUserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    customer_profile: CustomerProfileResponse | None = None

    model_config = {"from_attributes": True}