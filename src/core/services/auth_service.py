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
from src.utils.auth_utils import get_current_time


class AuthService:

    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    # ------------------------------------------------------------------ #
    #  Public methods                                                      #
    # ------------------------------------------------------------------ #

    async def register_customer(self, data: CustomerRegisterRequest) -> tuple[TokenResponse, str]:
        if await self.user_repo.get_by_email(data.email):
            raise UserAlreadyExistsException()

        role = await self.role_repo.get_by_name(RoleName.CUSTOMER.value)
        if not role:
            raise RuntimeError("CUSTOMER role not found. Make sure roles are seeded.")

        user = await self.user_repo.create(
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            role_id=role.id,
        )
        await self.customer_repo.create(
            user_id=user.id,
            phone=data.phone,
            customer_tier=data.customer_tier,
            preferred_contact=data.preferred_contact,
        )

        return await self._issue_tokens(
            user.id, data.email, RoleName.CUSTOMER.value, data.customer_tier, team_id=None
        )

    async def login(self, email: str, password: str) -> tuple[TokenResponse, str]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsException()
        if not user.is_active:
            raise InvalidCredentialsException("Account is deactivated")

        customer_tier = None
        team_id = None
        if user.role.name == RoleName.CUSTOMER.value:
            customer_tier = user.customer.customer_tier
        elif user.role.name in (RoleName.SUPPORT_AGENT.value, RoleName.TEAM_LEAD.value):
            team_id = user.led_teams[0].id if user.led_teams else None

        return await self._issue_tokens(user.id, user.email, user.role.name, customer_tier, team_id)

    async def refresh_access_token(self, refresh_token: str) -> tuple[AccessTokenResponse, str]:
        """
        Refresh token rotation logic
        """

        payload = decode_token(refresh_token)

        token_type = payload.get("type")
        if token_type != "refresh":
            raise InvalidTokenException("Not a refresh token")

        jti = payload.get("jti")
        if not jti:
            raise InvalidTokenException("Refresh token missing jti")

        record = await self.token_repo.get_by_jti(jti)

        if not record:
            raise InvalidTokenException("Refresh token not found")

        if record.revoked:
            raise InvalidTokenException("Refresh token already revoked")

        if record.expires_at < get_current_time():
            raise InvalidTokenException("Refresh token expired")

        # Extract payload values safely
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        customer_tier = payload.get("customer_tier")
        team_id = payload.get("team_id")

        if not user_id or not email or not role:
            raise InvalidTokenException("Invalid refresh token payload")

        # Convert user_id to int for DB usage
        user_id = int(user_id)

        #Token rotation
        await self.token_repo.revoke_by_jti(jti)

        token_response, new_refresh_token = await self._issue_tokens(
            user_id=user_id,
            user_email=email,
            user_role=role,
            customer_tier=customer_tier,
            team_id=team_id,
        )

        return (
            AccessTokenResponse(
                access_token=token_response.access_token,
                user=token_response.user,
            ),
            new_refresh_token,
        )
    

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return  # already logged out / cookie missing — treat as no-op

        try:
            payload = decode_token(refresh_token)
        except Exception:
            return  # invalid token on logout is fine, just clear the cookie

        jti = payload.get("jti")
        if jti:
            await self.token_repo.revoke_by_jti(jti)

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _issue_tokens(
        self,
        user_id: int,
        user_email: str,
        user_role: str,
        customer_tier: str | None,
        team_id: int | None,
    ) -> tuple[TokenResponse, str]:
        """Mint an access + refresh token pair, persist the refresh token, and return both."""
        access_token = create_access_token(user_id, user_email, user_role, customer_tier, team_id)
        refresh_token, jti, expires_at = create_refresh_token(user_id, user_email, user_role, customer_tier, team_id)

        await self.token_repo.create(user_id, jti, expires_at)

        token_response = TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=user_id,
                email=user_email,
                role=user_role,
                customer_tier=customer_tier,
                team_id=team_id,
            ),
        )
        return token_response, refresh_token