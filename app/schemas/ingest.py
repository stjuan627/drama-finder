from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import JobStage, JobStatus


class IngestEpisodeRequest(BaseModel):
    manifest_path: str = Field(min_length=1)
    series_id: str = Field(min_length=1, max_length=128)
    episode_id: str = Field(min_length=1, max_length=128)


class IngestJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_pk: UUID
    episode_pk: UUID
    status: JobStatus
    current_stage: JobStage | None
    progress_current: int
    progress_total: int
    attempt: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    artifacts: dict
