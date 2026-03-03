from enum import Enum

class CustomerTier(str, Enum):
    BASIC = "BASIC"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"


class PreferredContact(str, Enum):
    EMAIL = "EMAIL"
    WEB = "WEB"