"""User account status and email verification model."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.base import Base


class UserStatus(str, enum.Enum):
    """User account status for login and verification."""

    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    BANNED = "banned"


class UserAccountStatus(Base):
    """Account status and email verification state (1:1 with User)."""

    __tablename__ = "user_account_status"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        ENUM(
            UserStatus,
            name="user_status",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        server_default=UserStatus.PENDING_VERIFICATION.value,
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verification_code_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_code_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verification_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    verification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="account_status",
        single_parent=True,
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<UserAccountStatus(user_id={self.user_id!r}, status={self.status.value})>"


if TYPE_CHECKING:
    from app.models.user import User
