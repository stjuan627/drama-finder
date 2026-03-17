from __future__ import annotations

from app.db.session import SessionLocal
from app.services.ingest import IngestPipeline


def run_ingest_job(job_id: str) -> None:
    pipeline = IngestPipeline()
    with SessionLocal() as db:
        pipeline.run(db, job_id)
