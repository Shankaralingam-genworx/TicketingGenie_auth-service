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

import structlog
from src.observability.logging.logger import get_logger

logger = get_logger(__name__).bind(service="auth-service")

class AuthService:

    def __init__(self, db: AsyncSession):
        self.user_repo  = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    # Login 

    async def login(self, email: str, password: str) -> tuple[TokenResponse, str]:
        
        logger.info("login_flow_started")
        user = await self.user_repo.get_by_email(email)

        if not user or not verify_password(password, user.password_hash):
            logger.warning("login_failed_invalid_credentials")
            raise InvalidCredentialsException()
        if not user.is_active:
            logger.warning("login_failed_inactive_account", user_id=user.id)
            raise InvalidCredentialsException("Account is deactivated")
        
        structlog.contextvars.bind_contextvars(user_id=user.id)
        logger.info("login_success", user_id=user.id)

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

    #  Refresh

    async def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[AccessTokenResponse, str]:
       
        logger.info("refresh_token_flow_started")

        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            logger.warning("refresh_token_invalid_type")
            raise InvalidTokenException("Not a refresh token")

        jti = payload.get("jti")
        if not jti:
            logger.warning("refresh_token_missing_jti")
            raise InvalidTokenException("Refresh token missing jti")

        record = await self.token_repo.get_by_jti(jti)
        if not record:
            logger.warning("refresh_token_not_found")
            raise InvalidTokenException("Refresh token not found")
        if record.revoked:
            logger.warning("refresh_token_revoked")
            raise InvalidTokenException("Refresh token already revoked")
        if record.expires_at < get_current_time():
            logger.warning("refresh_token_expired")
            raise InvalidTokenException("Refresh token expired")

        # Rotate — revoke the used token before issuing a new one
        await self.token_repo.revoke_by_jti(jti)
        logger.info("refresh_token_revoked")

        # Fresh DB read — never use stale token claims for anything that can change
        user_id = int(payload["sub"])
        user    = await self.user_repo.get_by_id(user_id)

        if not user:
            logger.warning("refresh_token_user_not_found")
            raise InvalidTokenException("User no longer exists")
        if not user.is_active:
            logger.warning("refresh_token_user_inactive")
            raise InvalidTokenException("Account is deactivated")

        # Re-derive dynamic claims from current DB state
        customer_tier, team_id = self._resolve_claims(user)

        structlog.contextvars.bind_contextvars(user_id=user.id)
        logger.info("refresh_token_validated")

        token_response, new_refresh_token = await self._issue_tokens(
            user_id=user.id,
            user_email=user.email,
            user_role=user.role.name,
            customer_tier=customer_tier,
            team_id=team_id,
            org_id=user.org_id,
            must_change_password=user.must_change_password, 
        )

        logger.info("refresh_token_issued")

        return (
            AccessTokenResponse(
                access_token=token_response.access_token,
                user=token_response.user,
            ),
            new_refresh_token,
        )

    #  Logout 
    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            logger.info("logout_no_token_provided")
            return  
        try:
            payload = decode_token(refresh_token)
        except Exception:
            logger.warning("logout_invalid_token")
            return 

        jti = payload.get("jti")
        if jti:
            await self.token_repo.revoke_by_jti(jti)
            logger.info("logout_success")

    #  Private helpers 

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