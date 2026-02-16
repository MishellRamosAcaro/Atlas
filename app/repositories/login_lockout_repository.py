"""Login lockout repository for failed attempt tracking."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.login_lockout import LoginLockout

settings = get_settings()


class LoginLockoutRepository:
    """Repository for LoginLockout entity."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session

    def _normalize_email(self, email: str) -> str:
        """Normalize email for consistent storage."""
        return email.strip().lower()

    async def get_by_email(self, email: str) -> LoginLockout | None:
        """Get lockout record by email."""
        key = self._normalize_email(email)
        result = await self._session.execute(
            select(LoginLockout).where(LoginLockout.email == key)
        )
        return result.scalar_one_or_none()

    def is_locked(self, record: LoginLockout | None) -> tuple[bool, int | None]:
        """Check if record is locked. Returns (is_locked, minutes_remaining)."""
        if not record or not record.locked_until:
            return False, None
        now = datetime.now(timezone.utc)
        if record.locked_until <= now:
            return False, None
        delta = record.locked_until - now
        minutes = max(1, int(delta.total_seconds() / 60))
        return True, minutes

    async def record_failed_attempt(self, email: str) -> LoginLockout:
        """Increment failed attempts and lock if threshold exceeded."""
        key = self._normalize_email(email)
        now = datetime.now(timezone.utc)

        record = await self.get_by_email(key)
        if not record:
            record = LoginLockout(
                email=key,
                failed_attempts=0,
                locked_until=None,
            )
            self._session.add(record)
            await self._session.flush()

        # Reset count if previous lockout has expired
        if record.locked_until and record.locked_until <= now:
            record.failed_attempts = 0
            record.locked_until = None

        record.failed_attempts += 1
        record.updated_at = now

        if record.failed_attempts >= settings.max_failed_login_attempts:
            record.locked_until = now + timedelta(minutes=settings.lockout_minutes)

        self._session.add(record)
        await self._session.flush()
        return record

    async def clear(self, email: str) -> None:
        """Clear failed attempts on successful login."""
        key = self._normalize_email(email)
        result = await self._session.execute(
            select(LoginLockout).where(LoginLockout.email == key)
        )
        record = result.scalar_one_or_none()
        if record:
            await self._session.delete(record)
            await self._session.flush()
