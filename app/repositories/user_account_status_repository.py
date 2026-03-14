"""User account status repository for verification and status."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_account_status import UserAccountStatus, UserStatus


class UserAccountStatusRepository:
    """Repository for UserAccountStatus entity."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserAccountStatus | None:
        """Get account status by user ID."""
        result = await self._session.execute(
            select(UserAccountStatus).where(UserAccountStatus.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        status: UserStatus = UserStatus.PENDING_VERIFICATION,
    ) -> UserAccountStatus:
        """Create account status for a user."""
        record = UserAccountStatus(
            user_id=user_id,
            status=status,
            email_verified=False,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def update(self, record: UserAccountStatus) -> UserAccountStatus:
        """Update account status (flush to DB)."""
        self._session.add(record)
        await self._session.flush()
        return record

    def can_resend(self, record: UserAccountStatus, cooldown_minutes: int) -> bool:
        """Return True if enough time has passed since last send."""
        if not record.verification_sent_at:
            return True
        now = datetime.now(timezone.utc)
        return now >= record.verification_sent_at + timedelta(
            minutes=cooldown_minutes
        )

    def seconds_until_resend(
        self, record: UserAccountStatus, cooldown_minutes: int
    ) -> int:
        """Return seconds until resend is allowed (0 if allowed now)."""
        if not record.verification_sent_at:
            return 0
        now = datetime.now(timezone.utc)
        allowed_at = record.verification_sent_at + timedelta(
            minutes=cooldown_minutes
        )
        if now >= allowed_at:
            return 0
        return int((allowed_at - now).total_seconds())
