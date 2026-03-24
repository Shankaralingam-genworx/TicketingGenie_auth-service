"""User profile and password management."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.auth_constants import RoleName
from src.core.exceptions.auth_exceptions import (
    ForbiddenException,
    InvalidCredentialsException,
    UserNotFoundException,
)
from src.core.security import create_access_token, create_refresh_token
from src.data.repositories.refresh_token_repository import RefreshTokenRepository
from src.data.repositories.user_repository import UserRepository
from src.schemas.auth_schema import UserResponse
from src.schemas.user_schema import ChangePasswordResponse, UserSchemaResponse
from src.utils.password_utils import hash_password, verify_password
from src.observability.logging.logger import get_logger

logger = get_logger(__name__).bind(service="auth-service")


class UserService:

    def __init__(self, db: AsyncSession):
        self.repo       = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    async def get_user_by_id(self, user_id: int) -> UserSchemaResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            logger.warning("get_user_not_found", user_id=user_id)
            raise UserNotFoundException()
        return self._map(user)

    async def list_users(self) -> list[UserSchemaResponse]:
        logger.info("list_users_started")
        users = await self.repo.get_all()
        logger.info("list_users_success", count=len(users))
        return [self._map(u) for u in users]

    async def change_password(
        self,
        user_id: int,
        new_password: str,
        old_password: str | None = None,
    ) -> tuple[ChangePasswordResponse, str]:
        """
        Change password and issue a fresh token pair.
        Skips old_password check when must_change_password=True (forced reset).
        Revokes all existing sessions after the change.
        """
        logger.info("change_password_started", user_id=user_id)

        user = await self.repo.get_by_id(user_id)
        if not user:
            logger.warning("change_password_user_not_found", user_id=user_id)
            raise UserNotFoundException()

        # Skip current-password check on forced reset flows
        if not user.must_change_password:
            if not old_password:
                logger.warning("change_password_missing_old_password", user_id=user_id)
                raise ForbiddenException(
                    "Current password is required to change your password."
                )
            if not verify_password(old_password, user.password_hash):
                logger.warning("change_password_wrong_old_password", user_id=user_id)
                raise InvalidCredentialsException("Current password is incorrect.")

        await self.repo.update_password(user_id, hash_password(new_password))

        # Invalidate all existing sessions
        await self.token_repo.revoke_all_for_user(user_id)

        customer_tier, team_id = self._resolve_claims(user)

        access_token = create_access_token(
            user_id=user.id,
            user_email=user.email,
            role=user.role.name,
            customer_tier=customer_tier,
            team_id=team_id,
            org_id=user.org_id,
            must_change_password=False,
        )
        new_refresh_token, jti, expires_at = create_refresh_token(
            user_id=user.id,
            user_email=user.email,
            role=user.role.name,
            customer_tier=customer_tier,
            team_id=team_id,
            org_id=user.org_id,
        )
        await self.token_repo.create(user.id, jti, expires_at)

        logger.info("change_password_success", user_id=user_id)

        response = ChangePasswordResponse(
            message="Password changed successfully.",
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                email=user.email,
                role=user.role.name,
                customer_tier=customer_tier,
                team_id=team_id,
                org_id=user.org_id,
                must_change_password=False,
            ),
        )
        return response, new_refresh_token

    # ── Private helpers ─────────────────────
    
    @staticmethod
    def _resolve_claims(user) -> tuple[str | None, int | None]:
        """Derive customer_tier and team_id from current DB state."""
        customer_tier = None
        team_id       = None

        if user.role.name == RoleName.CUSTOMER.value and user.customer:
            customer_tier = user.customer.tier.name if user.customer.tier else None
        elif user.role.name == RoleName.TEAM_LEAD.value:
            team_id = user.led_teams[0].id if user.led_teams else None
        elif user.role.name == RoleName.SUPPORT_AGENT.value:
            team_id = (
                user.team_memberships[0].team_id
                if user.team_memberships else None
            )

        return customer_tier, team_id

    @staticmethod
    def _map(u) -> UserSchemaResponse:
        return UserSchemaResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role.name,
            is_active=u.is_active,
            must_change_password=u.must_change_password,
            org_id=u.org_id if u.org_id else None,
            org_name=u.organisation.name if u.organisation else None,
            created_at=u.created_at,
        )