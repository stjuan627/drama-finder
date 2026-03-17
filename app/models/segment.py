from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

settings = get_settings()


class Segment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    # 兼容首版迁移前已存在的 scenes 表，代码层统一使用 Segment 语义。
    __tablename__ = "scenes"

    episode_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_index: Mapped[int] = mapped_column("scene_index", Integer, nullable=False)
    start_ts: Mapped[float] = mapped_column(Float, nullable=False)
    end_ts: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    asr_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    representative_frame_paths: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    raw_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimension), nullable=True
    )

    episode = relationship("Episode", back_populates="segments")
    frames = relationship("Frame", back_populates="segment")
