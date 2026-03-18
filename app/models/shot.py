from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Shot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shots"

    episode_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ts: Mapped[float] = mapped_column(Float, nullable=False)
    end_ts: Mapped[float] = mapped_column(Float, nullable=False)
    raw_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    episode = relationship("Episode", back_populates="shots")
    frames = relationship("Frame", back_populates="shot")
