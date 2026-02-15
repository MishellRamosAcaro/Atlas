"""User repository for user CRUD operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository for User entity."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by ID."""
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email (canonical identifier)."""
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password_hash: str | None = None,
        roles: list[str] | None = None,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            roles=roles or ["user"],
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user: User) -> User:
        """Update user (flush to DB)."""
        self._session.add(user)
        await self._session.flush()
        return user
