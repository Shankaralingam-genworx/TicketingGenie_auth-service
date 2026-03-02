"""Business logic for user operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.auth_exceptions import UserNotFoundException
from src.data.repositories.user_repository import UserRepository
from src.schemas.user_schema import UserResponse


class UserService:
    """Handles user-related business logic."""

    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        """Get a user by their ID."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role.name,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    async def list_users(self) -> list[UserResponse]:
        """List all users (admin-only use case)."""
        users = await self.repo.get_all()
        return [
            UserResponse(
                id=u.id,
                name=u.name,
                email=u.email,
                role=u.role.name,
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in users
        ]
