from __future__ import annotations

from rq import Worker

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.queue import QueueService


def main() -> None:
    settings = get_settings()
    configure_logging(debug=settings.app_env == "development")
    queue_service = QueueService()
    worker = Worker(
        [queue_service._ingest_queue, queue_service._embedding_queue],
        connection=queue_service._redis,
    )
    worker.work()


if __name__ == "__main__":
    main()
