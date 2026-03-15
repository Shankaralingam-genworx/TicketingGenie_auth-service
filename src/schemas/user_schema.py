"""Pydantic schemas for user endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class UserResponse(BaseModel):
    id:                   int
    name:                 str
    email:                EmailStr
    role:                 str
    is_active:            bool
    must_change_password: bool
    org_id:               Optional[int]
    org_name:             Optional[str]
    created_at:           datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


class ChangePasswordRequest(BaseModel):
    """
    Body for POST /users/me/change-password.

    - old_password is OPTIONAL — the backend skips verification
      when must_change_password=True (first-login forced change).
    - new_password must be at least 8 characters.
    """
    old_password: Optional[str] = None
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters.")
        return v


class ChangePasswordResponse(BaseModel):
    message: str