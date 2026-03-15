"""Business logic for authentication: login, refresh, logout.

Customer self-registration has been removed.  Customers are now created by
their org_admin via POST /organisations/me/customers.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.core.exceptions.auth_exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
)
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from src.data.repositories.refresh_token_repository import RefreshTokenRepository
from src.data.repositories.user_repository import UserRepository
from src.schemas.auth_schema import AccessTokenResponse, TokenResponse, UserResponse
from src.utils.auth_utils import get_current_time


class AuthService:

    def __init__(self, db: AsyncSession):
        self.user_repo  = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    # ── Login ──────────────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> tuple[TokenResponse, str]:
        # Normalise email to lowercase before lookup — matches storage normalisation
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsException()
        if not user.is_active:
            raise InvalidCredentialsException("Account is deactivated")

        customer_tier, team_id = self._resolve_claims(user)

        return await self._issue_tokens(
            user_id=user.id,
            user_email=user.email,
            user_role=user.role.name,
            customer_tier=customer_tier,
            team_id=team_id,
            org_id=user.org_id,
            must_change_password=user.must_change_password,
        )

    # ── Refresh ────────────────────────────────────────────────────────────────

    async def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[AccessTokenResponse, str]:
        """
        Refresh token rotation.

        All dynamic claims (must_change_password, is_active, role, team_id,
        customer_tier) are re-derived from a fresh DB read on every refresh.
        This ensures that:
          - Password changes are reflected immediately on the next refresh.
          - Deactivated accounts are blocked.
          - Team reassignments are reflected without a full re-login.
        """
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
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

        # Rotate — revoke the used token before issuing a new one
        await self.token_repo.revoke_by_jti(jti)

        # Fresh DB read — never use stale token claims for anything that can change
        user_id = int(payload["sub"])
        user    = await self.user_repo.get_by_id(user_id)

        if not user:
            raise InvalidTokenException("User no longer exists")
        if not user.is_active:
            raise InvalidTokenException("Account is deactivated")

        # Re-derive dynamic claims from current DB state
        customer_tier, team_id = self._resolve_claims(user)

        token_response, new_refresh_token = await self._issue_tokens(
            user_id=user.id,
            user_email=user.email,
            user_role=user.role.name,
            customer_tier=customer_tier,
            team_id=team_id,
            org_id=user.org_id,
            must_change_password=user.must_change_password,  # always from DB
        )

        return (
            AccessTokenResponse(
                access_token=token_response.access_token,
                user=token_response.user,
            ),
            new_refresh_token,
        )

    # ── Logout ─────────────────────────────────────────────────────────────────

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return  # already logged out — treat as no-op
        try:
            payload = decode_token(refresh_token)
        except Exception:
            return  # invalid/expired token on logout is fine

        jti = payload.get("jti")
        if jti:
            await self.token_repo.revoke_by_jti(jti)

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_claims(user) -> tuple[str | None, int | None]:
        """
        Derive customer_tier and team_id from the user's DB state.
        Called both at login and at refresh to keep claims fresh.
        """
        customer_tier = None
        team_id       = None

        if user.role.name == RoleName.CUSTOMER.value and user.customer:
            customer_tier = user.customer.tier.name if user.customer.tier else None

        elif user.role.name == RoleName.TEAM_LEAD.value:
            # team_lead derives team_id from led_teams
            team_id = user.led_teams[0].id if user.led_teams else None

        elif user.role.name == RoleName.SUPPORT_AGENT.value:
            # support_agent derives team_id from team_memberships
            team_id = (
                user.team_memberships[0].team_id
                if user.team_memberships
                else None
            )

        return customer_tier, team_id

    async def _issue_tokens(
        self,
        user_id: int,
        user_email: str,
        user_role: str,
        customer_tier: str | None,
        team_id: int | None,
        org_id: int | None,
        must_change_password: bool,
    ) -> tuple[TokenResponse, str]:
        """Mint access + refresh tokens, persist the refresh record, return both."""
        access_token = create_access_token(
            user_id, user_email, user_role, customer_tier, team_id,
            org_id=org_id,
            must_change_password=must_change_password,
        )
        # must_change_password is intentionally NOT passed to create_refresh_token
        # so it is always re-read from the DB on the next refresh call.
        refresh_token, jti, expires_at = create_refresh_token(
            user_id, user_email, user_role, customer_tier, team_id,
            org_id=org_id,
        )

        await self.token_repo.create(user_id, jti, expires_at)

        token_response = TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=user_id,
                email=user_email,
                role=user_role,
                customer_tier=customer_tier,
                team_id=team_id,
                org_id=org_id,
                must_change_password=must_change_password,
            ),
        )
        return token_response, refresh_token