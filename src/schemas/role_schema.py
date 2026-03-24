"""Pydantic schemas for role endpoints."""

from datetime import datetime

from pydantic import BaseModel, field_validator


class RoleCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def normalise_name(cls, v: str) -> str:
        """Lowercase and strip whitespace."""
        return v.strip().lower()


class RoleUpdate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def normalise_name(cls, v: str) -> str:
        return v.strip().lower()


class RoleResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}