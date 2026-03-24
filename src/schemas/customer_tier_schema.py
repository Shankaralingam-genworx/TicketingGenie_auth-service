"""Pydantic schemas for customer tier endpoints."""

from datetime import datetime

from pydantic import BaseModel, field_validator


class CustomerTierCreate(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.strip().lower()


class CustomerTierUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def normalise(cls, v: str | None) -> str | None:
        return v.strip().lower() if v else v


class CustomerTierResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}