from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core import defaults


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = defaults.APP_NAME
    app_env: str = defaults.APP_ENV
    app_host: str = defaults.APP_HOST
    app_port: int = defaults.APP_PORT

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/drama_finder"
    )
    redis_url: str = "redis://localhost:6379/0"
    data_root: Path = defaults.DATA_ROOT
    manifest_root: Path = defaults.MANIFEST_ROOT

    gemini_api_key: str | None = None
    gemini_embedding_model: str = defaults.GEMINI_EMBEDDING_MODEL
    embedding_dimension: int = defaults.EMBEDDING_DIMENSION

    image_search_top_k: int = defaults.IMAGE_SEARCH_TOP_K
    text_search_top_k: int = defaults.TEXT_SEARCH_TOP_K
    frame_index_interval_seconds: float = defaults.FRAME_INDEX_INTERVAL_SECONDS
    asr_context_window_seconds: int = defaults.ASR_CONTEXT_WINDOW_SECONDS
    asr_model_name: str = defaults.ASR_MODEL_NAME
    asr_model_dir: str = defaults.ASR_MODEL_DIR
    asr_vad_model_name: str = defaults.ASR_VAD_MODEL_NAME
    asr_vad_model_dir: str = defaults.ASR_VAD_MODEL_DIR
    asr_device: str = defaults.ASR_DEVICE
    asr_cpu_cores: int = defaults.ASR_CPU_CORES
    asr_compute_type: str = defaults.ASR_COMPUTE_TYPE
    asr_stream_chunk_seconds: int = defaults.ASR_STREAM_CHUNK_SECONDS
    asr_vad_merge_gap_ms: int = defaults.ASR_VAD_MERGE_GAP_MS
    asr_segment_max_seconds: int = defaults.ASR_SEGMENT_MAX_SECONDS
    ingest_skip_embeddings: bool = defaults.INGEST_SKIP_EMBEDDINGS
    representative_frames_per_shot: int = defaults.REPRESENTATIVE_FRAMES_PER_SHOT
    low_confidence_threshold: float = defaults.LOW_CONFIDENCE_THRESHOLD
    job_timeout_seconds: int = defaults.JOB_TIMEOUT_SECONDS
    job_retry_count: int = defaults.JOB_RETRY_COUNT

    @property
    def manifests_path(self) -> Path:
        return self.manifest_root.resolve()

    @property
    def data_path(self) -> Path:
        return self.data_root.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
