"""Password hashing and verification using passlib with argon2."""

from passlib.context import CryptContext

# Using argon2 as the hashing algorithm
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if the plain-text password matches the hash."""
    return pwd_context.verify(plain_password, hashed_password)
