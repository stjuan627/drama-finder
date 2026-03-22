from __future__ import annotations

from redis import Redis
from rq import Queue

from app.core.config import get_settings

settings = get_settings()
INGEST_QUEUE_NAME = "ingest"
EMBEDDING_QUEUE_NAME = "embedding"


class QueueService:
    def __init__(self) -> None:
        self._redis = Redis.from_url(settings.redis_url)
        self._ingest_queue = Queue(
            INGEST_QUEUE_NAME,
            connection=self._redis,
            default_timeout=settings.job_timeout_seconds,
        )
        self._embedding_queue = Queue(
            EMBEDDING_QUEUE_NAME,
            connection=self._redis,
            default_timeout=settings.job_timeout_seconds,
        )

    def enqueue_ingest(self, job_id: str) -> str:
        from app.workers.tasks import run_ingest_job

        job = self._ingest_queue.enqueue(
            run_ingest_job, job_id, job_timeout=settings.job_timeout_seconds
        )
        return job.id

    def enqueue_frame_embedding(self, job_id: str) -> str:
        from app.workers.tasks import run_frame_embedding_job

        job = self._embedding_queue.enqueue(
            run_frame_embedding_job,
            job_id,
            job_timeout=settings.job_timeout_seconds,
        )
        return job.id
