"""Login lockout model for failed attempt tracking."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.base import Base


class LoginLockout(Base):
    """Tracks failed login attempts per email for account lockout."""

    __tablename__ = "login_lockouts"

    email: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        nullable=False,
    )
    failed_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<LoginLockout(email={self.email!r}, failed={self.failed_attempts}, locked_until={self.locked_until})>"
