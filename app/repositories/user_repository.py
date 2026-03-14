"""User repository for user CRUD operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User


class UserRepository:
    """Repository for User entity."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by ID (with account_status loaded for can_login)."""
        result = await self._session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.account_status))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email (canonical identifier; with account_status)."""
        result = await self._session.execute(
            select(User)
            .where(User.email == email)
            .options(selectinload(User.account_status))
        )
        return result.scalar_one_or_none()

    async def get_by_email_excluding(self, email: str, exclude_user_id: uuid.UUID) -> User | None:
        """Get user by email if they exist and are not the excluded user."""
        result = await self._session.execute(
            select(User).where(User.email == email).where(User.id != exclude_user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password_hash: str | None = None,
        roles: list[str] | None = None,
        country_code: str = "",
        phone_number_normalized: str = "",
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            roles=roles or ["user"],
            country_code=country_code,
            phone_number_normalized=phone_number_normalized,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user: User) -> User:
        """Update user (flush to DB)."""
        self._session.add(user)
        await self._session.flush()
        return user

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """Delete user by ID. Returns True if deleted. CASCADE removes related rows."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        await self._session.delete(user)
        await self._session.flush()
        return True
