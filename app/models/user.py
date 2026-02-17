"""User model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.base import Base


class User(Base):
    """User entity.

    Canonical identifier: email. Supports local (email/password) and OAuth (Google) login.
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
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{user}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
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

    oauth_identities: Mapped[list["OAuthIdentity"]] = relationship(
        "OAuthIdentity",
        back_populates="user",
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
        """Whether the user is allowed to log in."""
        return self.is_active and not self.is_banned


if TYPE_CHECKING:
    from app.models.file import File
    from app.models.oauth_identity import OAuthIdentity
    from app.models.refresh_token import RefreshToken
