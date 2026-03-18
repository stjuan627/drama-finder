from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EpisodeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=64)
    episode_no: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    filename: str = Field(min_length=1, max_length=255)

    @field_validator("filename")
    @classmethod
    def filename_must_be_relative(cls, value: str) -> str:
        if Path(value).is_absolute():
            raise ValueError("filename 必须是相对路径")
        return value


class SeriesManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "v1"
    series_id: str = Field(min_length=1, max_length=64)
    series_title: str = Field(min_length=1, max_length=255)
    season_label: str | None = Field(default=None, max_length=128)
    language: str = Field(default="zh-CN", max_length=32)
    video_root: str = Field(min_length=1, max_length=512)
    intro_duration_seconds: float = Field(default=0, ge=0)
    outro_duration_seconds: float = Field(default=0, ge=0)
    episodes: list[EpisodeManifest] = Field(default_factory=list, min_length=1)

    @field_validator("version")
    @classmethod
    def version_must_be_v1(cls, value: str) -> str:
        if value != "v1":
            raise ValueError("当前仅支持 manifest v1")
        return value
