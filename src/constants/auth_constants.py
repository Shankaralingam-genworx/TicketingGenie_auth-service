"""Auth-related constants used across the service."""

from enum import Enum


class RoleName(str, Enum):
    CUSTOMER = "CUSTOMER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    TEAM_LEAD = "TEAM_LEAD"
    ADMIN = "ADMIN"


TOKEN_TYPE = "bearer"
