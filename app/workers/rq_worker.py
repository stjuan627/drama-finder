from __future__ import annotations

from rq import Worker

from app.services.queue import QueueService


def main() -> None:
    queue_service = QueueService()
    worker = Worker([queue_service._queue], connection=queue_service._redis)
    worker.work()


if __name__ == "__main__":
    main()
