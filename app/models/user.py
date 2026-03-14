"""User model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.base import Base


class User(Base):
    """User entity.

    Canonical identifier: email. Supports local (email/password) login.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_code: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{user}",
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

    account_status: Mapped["UserAccountStatus"] = relationship(
        "UserAccountStatus",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["File"]] = relationship(
        "File",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<User(id={self.id!r}, email={self.email!r})>"

    @property
    def name(self) -> str:
        """Full display name (first_name + last_name)."""
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def can_login(self) -> bool:
        """Whether the user is allowed to log in (active and verified)."""
        if not self.account_status:
            return False
        from app.models.user_account_status import UserStatus

        return self.account_status.status == UserStatus.ACTIVE


if TYPE_CHECKING:
    from app.models.file import File
    from app.models.refresh_token import RefreshToken
    from app.models.user_account_status import UserAccountStatus
