from __future__ import annotations

from datetime import datetime
from typing import Literal
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


IngestEpisodeState = Literal["not_ingested", "ingested", "queued", "running", "failed"]


class ManifestSummaryRead(BaseModel):
    manifest_path: str
    series_id: str
    series_title: str
    season_label: str | None
    language: str
    episode_count: int


class EpisodeIngestStatusRead(BaseModel):
    episode_id: str
    episode_no: int
    title: str
    filename: str
    ingest_state: IngestEpisodeState
    is_ingested: bool
    frame_count: int = Field(ge=0)
    latest_job_id: UUID | None
    latest_job_status: JobStatus | None
    latest_job_stage: JobStage | None
    latest_error_message: str | None
    latest_finished_at: datetime | None
