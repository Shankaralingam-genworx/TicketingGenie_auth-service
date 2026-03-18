"""Business logic for user operations."""

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


class UserService:
    """Handles user-related business logic."""

    def __init__(self, db: AsyncSession):
        self.repo        = UserRepository(db)
        self.token_repo  = RefreshTokenRepository(db)

    async def get_user_by_id(self, user_id: int) -> UserSchemaResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        return self._map(user)

    async def list_users(self) -> list[UserSchemaResponse]:
        users = await self.repo.get_all()
        return [self._map(u) for u in users]

    async def change_password(
        self,
        user_id: int,
        new_password: str,
        old_password: str | None = None,
    ) -> tuple[ChangePasswordResponse, str]:
        """
        Change a user's password then immediately issue a fresh token pair.

        Flow:
          1. Validate old_password (skipped when must_change_password=True).
          2. Hash and store the new password; clear must_change_password flag.
          3. Revoke ALL existing refresh tokens for this user so stale sessions
             cannot be used after a password change.
          4. Mint a brand-new access token + refresh token with
             must_change_password=False baked in.
          5. Return the new access token in the response body and the new
             refresh token to the caller (route handler sets it as a cookie).

        Returns:
            (ChangePasswordResponse, new_refresh_token_string)
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        # ── Validate current password ──────────────────────────────────────────
        if not user.must_change_password:
            if not old_password:
                raise ForbiddenException(
                    "Current password is required to change your password."
                )
            if not verify_password(old_password, user.password_hash):
                raise InvalidCredentialsException("Current password is incorrect.")

        # ── Update password in DB (clears must_change_password flag) ───────────
        await self.repo.update_password(user_id, hash_password(new_password))

        # ── Revoke all existing refresh tokens (security hygiene) ──────────────
        await self.token_repo.revoke_all_for_user(user_id)

        # ── Re-derive role-specific claims from current DB state ───────────────
        customer_tier, team_id = self._resolve_claims(user)

        # ── Mint fresh access + refresh tokens ─────────────────────────────────
        # must_change_password is now False — this is reflected in the new tokens
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
                must_change_password=False,   # ← always False after a successful change
            ),
        )
        return response, new_refresh_token

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_claims(user) -> tuple[str | None, int | None]:
        """Derive customer_tier and team_id from the user's current DB state."""
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