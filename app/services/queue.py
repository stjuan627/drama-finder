from __future__ import annotations

from redis import Redis
from rq import Queue

from app.core.config import get_settings

settings = get_settings()


class QueueService:
    def __init__(self) -> None:
        self._redis = Redis.from_url(settings.redis_url)
        self._queue = Queue(
            "ingest",
            connection=self._redis,
            default_timeout=settings.job_timeout_seconds,
        )

    def enqueue_ingest(self, job_id: str) -> str:
        from app.workers.tasks import run_ingest_job

        job = self._queue.enqueue(run_ingest_job, job_id)
        return job.id
