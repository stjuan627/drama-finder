from __future__ import annotations

from app.services.queue import QueueService


class FakeEnqueueResult:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


class FakeQueue:
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self.calls: list[tuple[object, tuple[object, ...], dict[str, object]]] = []

    def enqueue(self, func: object, *args: object, **kwargs: object) -> FakeEnqueueResult:
        self.calls.append((func, args, kwargs))
        return FakeEnqueueResult(self.job_id)


def test_enqueue_ingest_uses_ingest_queue() -> None:
    service = QueueService()
    fake_queue = FakeQueue("ingest-job")
    service.__dict__["_ingest_queue"] = fake_queue

    job_id = service.enqueue_ingest("abc")

    assert job_id == "ingest-job"
    assert fake_queue.calls[0][1] == ("abc",)


def test_enqueue_frame_embedding_uses_embedding_queue() -> None:
    service = QueueService()
    fake_queue = FakeQueue("embedding-job")
    service.__dict__["_embedding_queue"] = fake_queue

    job_id = service.enqueue_frame_embedding("xyz")

    assert job_id == "embedding-job"
    assert fake_queue.calls[0][1] == ("xyz",)
