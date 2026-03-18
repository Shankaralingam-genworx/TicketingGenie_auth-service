"""Pydantic schemas for user endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from src.schemas.auth_schema import UserResponse


class UserListResponse(BaseModel):
    users: list["UserSchemaResponse"]
    total: int


class UserSchemaResponse(BaseModel):
    id:                   int
    name:                 str
    email:                EmailStr
    role:                 str
    is_active:            bool
    must_change_password: bool
    org_id:               Optional[int] = None
    org_name:             Optional[str] = None
    created_at:           datetime

    model_config = {"from_attributes": True}


# Rebuild forward reference
UserListResponse.model_rebuild()


class ChangePasswordRequest(BaseModel):

    old_password: Optional[str] = None
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters.")
        return v


class ChangePasswordResponse(BaseModel):
  
    message:      str
    access_token: str
    token_type:   str         = "bearer"
    user:         UserResponse