from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

settings = get_settings()


class Frame(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "frames"

    episode_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shot_pk: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scene_pk: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    frame_index: Mapped[int] = mapped_column(nullable=False)
    frame_ts: Mapped[float] = mapped_column(Float, nullable=False)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    context_asr_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimension), nullable=True
    )

    episode = relationship("Episode", back_populates="frames")
    shot = relationship("Shot", back_populates="frames")
    scene = relationship("Scene", back_populates="frames")
