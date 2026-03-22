from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.db.session import SessionLocal
from app.models.ingest_job import IngestJob
from app.services.ingest import IngestPipeline


def run_ingest_job(job_id: str) -> None:
    pipeline = IngestPipeline()
    with SessionLocal() as db:
        pipeline.run(db, job_id)


def run_frame_embedding_job(job_id: str) -> None:
    pipeline = IngestPipeline()
    with SessionLocal() as db:
        job = db.get(IngestJob, UUID(job_id))
        if job is None:
            raise ValueError(f"job not found: {job_id}")

        artifacts = dict(job.artifacts or {})
        artifacts["embedding_status"] = "running"
        artifacts["embedding_started_at"] = datetime.now(UTC).isoformat()
        db.add(job)
        job.artifacts = artifacts
        db.commit()

        try:
            result = pipeline.backfill_frame_embeddings(db, job.episode_pk)
        except Exception as exc:
            db.refresh(job)
            artifacts = dict(job.artifacts or {})
            artifacts["embedding_status"] = "failed"
            artifacts["embedding_error"] = str(exc)
            artifacts["embedding_finished_at"] = datetime.now(UTC).isoformat()
            job.artifacts = artifacts
            db.add(job)
            db.commit()
            raise

        db.refresh(job)
        artifacts = dict(job.artifacts or {})
        artifacts["embedding_status"] = "completed"
        artifacts["embedding_error"] = None
        artifacts["embedding_finished_at"] = datetime.now(UTC).isoformat()
        artifacts["embedding_backfill"] = result
        job.artifacts = artifacts
        db.add(job)
        db.commit()
