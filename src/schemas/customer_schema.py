"""Pydantic schemas for customer registration and profile."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class CustomerRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    company_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class CustomerProfileResponse(BaseModel):
    id: str
    user_id: str
    phone: str | None
    company_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CurrentUserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    customer_profile: CustomerProfileResponse | None = None

    model_config = {"from_attributes": True}
