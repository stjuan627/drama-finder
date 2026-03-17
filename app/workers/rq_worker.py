from __future__ import annotations

from rq import Connection, Worker

from app.services.queue import get_queue, get_redis_connection


def main() -> None:
    connection = get_redis_connection()
    queue = get_queue()
    with Connection(connection):
        worker = Worker([queue], connection=connection)
        worker.work()


if __name__ == "__main__":
    main()
