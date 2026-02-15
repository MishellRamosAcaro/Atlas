"""OAuth identity model for linking provider accounts to users."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.base import Base


class OAuthIdentity(Base):
    """OAuth provider identity linked to a user.

    One user can have multiple OAuth identities (e.g. multiple Google accounts).
    """

    __tablename__ = "oauth_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="oauth_identities")

    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_oauth_identities_provider_user"
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<OAuthIdentity(provider={self.provider!r}, provider_user_id={self.provider_user_id!r})>"
