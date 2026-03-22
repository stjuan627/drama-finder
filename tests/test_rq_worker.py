from __future__ import annotations

from types import SimpleNamespace

from app.workers import rq_worker


def test_main_listens_to_ingest_and_embedding_queues(monkeypatch) -> None:
    created: dict[str, object] = {}

    class FakeWorker:
        def __init__(self, queues: list[object], connection: object) -> None:
            created["queues"] = queues
            created["connection"] = connection

        def work(self) -> None:
            created["worked"] = True

    fake_queue_service = SimpleNamespace(
        _ingest_queue="ingest-queue",
        _embedding_queue="embedding-queue",
        _redis="redis-conn",
    )

    monkeypatch.setattr(rq_worker, "QueueService", lambda: fake_queue_service)
    monkeypatch.setattr(rq_worker, "Worker", FakeWorker)

    rq_worker.main()

    assert created["queues"] == ["ingest-queue", "embedding-queue"]
    assert created["connection"] == "redis-conn"
    assert created["worked"] is True
