"""Pydantic schemas for role endpoints."""

from datetime import datetime

from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
