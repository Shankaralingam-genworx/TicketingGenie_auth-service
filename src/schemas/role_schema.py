"""Pydantic schemas for role endpoints."""

from datetime import datetime

from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
