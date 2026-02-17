"""File upload model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.base import Base

# Status after scan: pending, clean, infected, or scan failed
FILE_STATUS_PENDING = "PENDING_SCAN"
FILE_STATUS_CLEAN = "CLEAN"
FILE_STATUS_INFECTED = "INFECTED"
FILE_STATUS_FAILED_SCAN = "FAILED_SCAN"


class File(Base):
    """File upload entity.

    One record per uploaded file. status controls visibility and download.
    """

    __tablename__ = "files"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=FILE_STATUS_PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scan_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    scan_provider: Mapped[str] = mapped_column(Text, nullable=False, default="")

    user: Mapped["User"] = relationship("User", back_populates="files")

    __table_args__ = (
        Index("ix_files_user_id_created_at", "user_id", "created_at"),
        Index("ix_files_user_id_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<File(file_id={self.file_id!r}, user_id={self.user_id!r}, status={self.status!r})>"

    @property
    def is_clean(self) -> bool:
        """Whether the file is safe to list and download."""
        return self.status == FILE_STATUS_CLEAN

    @property
    def is_listable(self) -> bool:
        """Whether to include in GET /uploads list (CLEAN or optionally PENDING_SCAN)."""
        return self.status in (FILE_STATUS_CLEAN, FILE_STATUS_PENDING)


if TYPE_CHECKING:
    from app.models.user import User
