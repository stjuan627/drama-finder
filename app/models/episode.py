from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Episode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint("series_pk", "episode_id"),
        UniqueConstraint("series_pk", "episode_no"),
    )

    series_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("series.id", ondelete="CASCADE"), nullable=False, index=True
    )
    episode_id: Mapped[str] = mapped_column(String(128), nullable=False)
    episode_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    video_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    series = relationship("Series", back_populates="episodes")
    ingest_jobs = relationship("IngestJob", back_populates="episode")
    shots = relationship("Shot", back_populates="episode", cascade="all, delete-orphan")
    scenes = relationship("Scene", back_populates="episode", cascade="all, delete-orphan")
    frames = relationship("Frame", back_populates="episode", cascade="all, delete-orphan")
