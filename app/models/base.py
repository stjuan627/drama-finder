from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class JobStage(enum.StrEnum):
    MANIFEST = "manifest"
    AUDIO_EXTRACTION = "audio_extraction"
    ASR = "asr"
    SHOT_DETECTION = "shot_detection"
    FRAME_EXTRACTION = "frame_extraction"
    REPRESENTATIVE_FRAMES = "representative_frames"
    SCENE_MERGE = "scene_merge"
    EMBEDDINGS = "embeddings"
    PERSIST = "persist"

    # 兼容旧数据库枚举值，代码中优先使用新的 segment 语义别名。
    SHOT_KEYFRAMES = "representative_frames"
    SEGMENT_BUILD = "scene_merge"
