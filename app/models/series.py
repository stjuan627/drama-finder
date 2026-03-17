from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Series(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "series"

    series_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    season_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="zh-CN")
    manifest_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    episodes = relationship("Episode", back_populates="series", cascade="all, delete-orphan")
    ingest_jobs = relationship("IngestJob", back_populates="series")
