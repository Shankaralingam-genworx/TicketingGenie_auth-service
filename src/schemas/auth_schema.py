"""Pydantic schemas for authentication endpoints."""

from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id:                   int
    email:                str
    role:                 str
    customer_tier:        Optional[str] = None
    team_id:              Optional[int] = None
    org_id:               Optional[int] = None   # set for org_admin and customer
    must_change_password: bool = False            # frontend guards on this

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserResponse