from enum import Enum

class CustomerTier(str, Enum):
    ENTERPRISE = "enterprise"
    SMB = "smb"


class PreferredContact(str, Enum):
    EMAIL = "email"
    WEB = "web"