"""Business logic for user operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.auth_exceptions import (
    ForbiddenException,
    InvalidCredentialsException,
    UserNotFoundException,
)
from src.data.repositories.user_repository import UserRepository
from src.schemas.user_schema import ChangePasswordResponse, UserResponse
from src.utils.password_utils import hash_password, verify_password


class UserService:
    """Handles user-related business logic."""

    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        """Get a user by their ID."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        return self._map(user)

    async def list_users(self) -> list[UserResponse]:
        """List all users (admin-only use case)."""
        users = await self.repo.get_all()
        return [self._map(u) for u in users]

    async def change_password(
        self,
        user_id: int,
        new_password: str,
        old_password: str | None = None,
    ) -> ChangePasswordResponse:
        """
        Change a user's password.

        Rules:
        - If must_change_password=True  → skip old_password verification
          (first-login forced change — no old password known by user).
        - If must_change_password=False → old_password is required and must
          match the current hash.

        After a successful change must_change_password is always set to False.
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        if not user.must_change_password:
            # Normal change — old password must be supplied and correct
            if not old_password:
                raise ForbiddenException(
                    "Current password is required to change your password."
                )
            if not verify_password(old_password, user.password_hash):
                raise InvalidCredentialsException(
                    "Current password is incorrect."
                )

        # Hash and persist the new password; clear the flag
        new_hash = hash_password(new_password)
        await self.repo.update_password(user_id, new_hash)

        return ChangePasswordResponse(message="Password changed successfully.")

    @staticmethod
    def _map(u) -> UserResponse:
        return UserResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role.name,
            is_active=u.is_active,
            must_change_password=u.must_change_password,
            org_id=u.org_id if hasattr(u, "org_id") else None,
            org_name=u.organisation.name if (hasattr(u, "organisation") and u.organisation) else None,
            created_at=u.created_at,
        )