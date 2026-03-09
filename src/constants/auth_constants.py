"""Auth-related constants used across the service."""

from enum import Enum


class RoleName(str, Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    TEAM_LEAD = "team_lead"
    ADMIN = "admin"


TOKEN_TYPE = "bearer"
