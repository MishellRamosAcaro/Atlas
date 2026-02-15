"""OAuth identity repository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_identity import OAuthIdentity


class OAuthIdentityRepository:
    """Repository for OAuthIdentity entity."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session

    async def get_by_provider_user(
        self,
        provider: str,
        provider_user_id: str,
    ) -> OAuthIdentity | None:
        """Get OAuth identity by provider and provider user ID."""
        result = await self._session.execute(
            select(OAuthIdentity).where(
                OAuthIdentity.provider == provider,
                OAuthIdentity.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        provider: str,
        provider_user_id: str,
    ) -> OAuthIdentity:
        """Create a new OAuth identity."""
        identity = OAuthIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
        self._session.add(identity)
        await self._session.flush()
        return identity
