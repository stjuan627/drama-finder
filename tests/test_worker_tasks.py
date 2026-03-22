from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.workers import tasks as worker_tasks


class FakeDB:
    def __init__(self, job: object) -> None:
        self.job = job
        self.commits = 0

    def get(self, model: object, key: object) -> object | None:
        del model
        return self.job if str(getattr(self.job, "id", "")) == str(key) else None

    def add(self, _value: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, _value: object) -> None:
        return None


def test_run_frame_embedding_job_marks_completed(monkeypatch) -> None:
    job = SimpleNamespace(
        id=uuid4(),
        episode_pk=uuid4(),
        artifacts={"embedding_status": "queued"},
    )
    db = FakeDB(job)

    @contextmanager
    def fake_session_local():
        yield db

    class FakePipeline:
        def backfill_frame_embeddings(
            self,
            passed_db: object,
            episode_pk: object,
            max_workers: int,
            progress_callback=None,
        ) -> dict[str, int]:
            assert passed_db is db
            assert episode_pk == job.episode_pk
            assert max_workers == worker_tasks.settings.frame_embedding_max_workers
            if progress_callback is not None:
                progress_callback(
                    {"pending": 2, "processed": 2, "updated": 2, "failed": 0, "remaining": 0}
                )
            return {"pending": 2, "processed": 2, "updated": 2, "failed": 0, "remaining": 0}

    monkeypatch.setattr(worker_tasks, "SessionLocal", fake_session_local)
    monkeypatch.setattr(worker_tasks, "IngestPipeline", FakePipeline)

    worker_tasks.run_frame_embedding_job(str(job.id))

    assert job.artifacts["embedding_status"] == "completed"
    assert job.artifacts["embedding_backfill"] == {
        "pending": 2,
        "processed": 2,
        "updated": 2,
        "failed": 0,
        "remaining": 0,
    }
    assert job.artifacts["embedding_progress"] == {
        "pending": 2,
        "processed": 2,
        "updated": 2,
        "failed": 0,
        "remaining": 0,
    }
    assert job.artifacts["embedding_error"] is None
    assert datetime.fromisoformat(job.artifacts["embedding_started_at"]).tzinfo == UTC
    assert datetime.fromisoformat(job.artifacts["embedding_finished_at"]).tzinfo == UTC


def test_run_frame_embedding_job_marks_failed(monkeypatch) -> None:
    job = SimpleNamespace(
        id=uuid4(),
        episode_pk=uuid4(),
        artifacts={"embedding_status": "queued"},
    )
    db = FakeDB(job)

    @contextmanager
    def fake_session_local():
        yield db

    class FakePipeline:
        def backfill_frame_embeddings(
            self,
            passed_db: object,
            episode_pk: object,
            max_workers: int,
            progress_callback=None,
        ) -> dict[str, int]:
            assert passed_db is db
            assert episode_pk == job.episode_pk
            assert max_workers == worker_tasks.settings.frame_embedding_max_workers
            raise RuntimeError("boom")

    monkeypatch.setattr(worker_tasks, "SessionLocal", fake_session_local)
    monkeypatch.setattr(worker_tasks, "IngestPipeline", FakePipeline)

    try:
        worker_tasks.run_frame_embedding_job(str(job.id))
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("expected RuntimeError")

    assert job.artifacts["embedding_status"] == "failed"
    assert job.artifacts["embedding_error"] == "boom"
    assert datetime.fromisoformat(job.artifacts["embedding_finished_at"]).tzinfo == UTC


def test_run_frame_embedding_job_initializes_progress(monkeypatch) -> None:
    job = SimpleNamespace(
        id=uuid4(),
        episode_pk=uuid4(),
        artifacts={"embedding_status": "queued", "pending_frame_embeddings": 5},
    )
    db = FakeDB(job)

    @contextmanager
    def fake_session_local():
        yield db

    class FakePipeline:
        def backfill_frame_embeddings(
            self, passed_db: object, episode_pk: object, max_workers: int, progress_callback
        ) -> dict[str, int]:
            assert passed_db is db
            assert episode_pk == job.episode_pk
            assert max_workers == worker_tasks.settings.frame_embedding_max_workers
            progress_callback(
                {"pending": 5, "processed": 2, "updated": 2, "failed": 0, "remaining": 3}
            )
            return {"pending": 5, "processed": 5, "updated": 5, "failed": 0, "remaining": 0}

    monkeypatch.setattr(worker_tasks, "SessionLocal", fake_session_local)
    monkeypatch.setattr(worker_tasks, "IngestPipeline", FakePipeline)

    worker_tasks.run_frame_embedding_job(str(job.id))

    assert job.artifacts["embedding_progress"] == {
        "pending": 5,
        "processed": 5,
        "updated": 5,
        "failed": 0,
        "remaining": 0,
    }
