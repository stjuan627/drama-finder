from __future__ import annotations

from workers.jobs import run_episode_ingest_job


def run_ingest_job(job_id: str) -> None:
    run_episode_ingest_job(job_id)
