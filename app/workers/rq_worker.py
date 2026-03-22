from __future__ import annotations

from rq import Worker

from app.services.queue import QueueService


def main() -> None:
    queue_service = QueueService()
    worker = Worker(
        [queue_service._ingest_queue, queue_service._embedding_queue],
        connection=queue_service._redis,
    )
    worker.work()


if __name__ == "__main__":
    main()
