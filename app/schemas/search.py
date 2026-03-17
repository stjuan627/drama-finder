from __future__ import annotations

from pydantic import BaseModel, Field


class SearchTextRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=3, ge=1, le=10)


class SearchHit(BaseModel):
    series_id: str
    episode_id: str
    matched_start_ts: float
    matched_end_ts: float
    score: float
    segment_summary: str | None
    evidence_images: list[str]
    evidence_text: list[str]


class SearchImageResponse(BaseModel):
    hits: list[SearchHit]
    low_confidence: bool
