"""Refresh token repository for session management."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository for RefreshToken entity."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Get refresh token by hash."""
        result = await self._session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.expires_at > datetime.now(timezone.utc))
        )
        return result.scalar_one_or_none()

    async def count_active_by_user(self, user_id: uuid.UUID) -> int:
        """Count active (non-expired) refresh tokens for user."""
        result = await self._session.execute(
            select(func.count(RefreshToken.id))
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.expires_at > datetime.now(timezone.utc))
        )
        return result.scalar() or 0

    async def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> RefreshToken:
        """Create a new refresh token."""
        now = datetime.now(timezone.utc)
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            last_used_at=now,
            user_agent=user_agent,
            client_ip=client_ip,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def delete_by_id(self, token_id: uuid.UUID) -> None:
        """Delete refresh token by ID."""
        await self._session.execute(
            delete(RefreshToken).where(RefreshToken.id == token_id)
        )
        await self._session.flush()

    async def delete_by_token_hash(self, token_hash: str) -> None:
        """Delete refresh token by hash."""
        await self._session.execute(
            delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        await self._session.flush()

    async def delete_all_by_user(self, user_id: uuid.UUID) -> None:
        """Delete all refresh tokens for user (global logout)."""
        await self._session.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        await self._session.flush()

    async def delete_oldest_for_user(self, user_id: uuid.UUID) -> None:
        """Delete the oldest (by last_used_at) refresh token for user."""
        subq = (
            select(RefreshToken.id)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.expires_at > datetime.now(timezone.utc))
            .order_by(RefreshToken.last_used_at.asc())
            .limit(1)
        )
        result = await self._session.execute(subq)
        token_id = result.scalar_one_or_none()
        if token_id:
            await self.delete_by_id(token_id)

    async def update_last_used(
        self,
        token: RefreshToken,
        last_used_at: datetime | None = None,
    ) -> None:
        """Update last_used_at for idle timeout."""
        token.last_used_at = last_used_at or datetime.now(timezone.utc)
        self._session.add(token)
        await self._session.flush()
