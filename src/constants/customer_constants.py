from enum import Enum


class PreferredContact(str, Enum):
    EMAIL = "email"
    WEB = "web"