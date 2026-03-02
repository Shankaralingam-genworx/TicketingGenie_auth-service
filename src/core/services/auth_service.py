"""Business logic for authentication: register, login, refresh, logout."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.core.exceptions.auth_exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    UserAlreadyExistsException,
)
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.data.repositories.customer_repository import CustomerRepository
from src.data.repositories.refresh_token_repository import RefreshTokenRepository
from src.data.repositories.role_repository import RoleRepository
from src.data.repositories.user_repository import UserRepository
from src.schemas.auth_schema import AccessTokenResponse, TokenResponse, UserResponse
from src.schemas.customer_schema import CustomerRegisterRequest


class AuthService:
    """Handles authentication flows."""

    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    async def register_customer(self, data: CustomerRegisterRequest) -> TokenResponse:
        """
        Register a new customer user and create their customer profile.
        Returns tokens immediately so the user is logged in after registration.
        """
        # Check if email already taken
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise UserAlreadyExistsException()

        # Get the CUSTOMER role
        role = await self.role_repo.get_by_name(RoleName.CUSTOMER.value)
        if not role:
            raise RuntimeError("CUSTOMER role not found. Make sure roles are seeded.")

        # Create the user
        password_hash = hash_password(data.password)
        user = await self.user_repo.create(
            name=data.name,
            email=data.email,
            password_hash=password_hash,
            role_id=role.id,
        )

        # Create the customer profile
        await self.customer_repo.create(
            user_id=user.id,
            phone=data.phone,
            company_name=data.company_name,
        )

        # Issue tokens
        return await self._issue_tokens(user.id, data.email, RoleName.CUSTOMER.value)
       

    async def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate a user with email/password and return tokens."""
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InvalidCredentialsException("Account is deactivated")

        return await self._issue_tokens(user.id,user.email,user.role.name)

    async def refresh_access_token(self, refresh_token: str) -> AccessTokenResponse:
        """Exchange a valid refresh token for a new access token."""
        # Validate JWT first
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidTokenException("Not a refresh token")

        # Check DB record
        token_record = await self.token_repo.get_by_token(refresh_token)
        if not token_record or token_record.revoked:
            raise InvalidTokenException("Refresh token is invalid or revoked")

        # Check expiry (belt-and-suspenders, jose already checks exp)
        if token_record.expires_at < datetime.now(timezone.utc):
            raise InvalidTokenException("Refresh token has expired")

        user_id = payload["sub"]
        role = payload["role"]
        access_token = create_access_token(user_id, role)
        return AccessTokenResponse(access_token=access_token)

    async def logout(self, refresh_token: str) -> None:
        """Revoke the given refresh token (logout)."""
        revoked = await self.token_repo.revoke(refresh_token)
        if not revoked:
            raise InvalidTokenException("Refresh token not found")

    async def _issue_tokens(
     self, user_id: str, user_email: str, user_role: str) -> tuple[TokenResponse, str]:
        
     """Create tokens and return response + refresh token separately."""
     
     access_token = create_access_token(user_id, user_role)
     refresh_token, expires_at = create_refresh_token(user_id, user_role)
 
     await self.token_repo.create(user_id, refresh_token, expires_at)
 
     token_response = TokenResponse(
         access_token=access_token,
         user=UserResponse(
             id=user_id,
             email=user_email,
             role=user_role
         )
     )
 
     return token_response, refresh_token