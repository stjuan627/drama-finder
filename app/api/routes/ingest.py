from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.ingest_job import IngestJob
from app.schemas.ingest import IngestEpisodeRequest, IngestJobRead
from app.services.ingest import IngestService
from app.services.manifest import ManifestError

router = APIRouter(prefix="/ingest", tags=["ingest"])
service = IngestService()


@router.post("/episode", response_model=IngestJobRead, status_code=status.HTTP_202_ACCEPTED)
def submit_ingest(
    payload: IngestEpisodeRequest,
    db: Annotated[Session, Depends(get_db)],
) -> IngestJob:
    try:
        return service.submit(db, payload)
    except ManifestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{job_id}", response_model=IngestJobRead)
def get_ingest_job(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> IngestJob:
    job = db.get(IngestJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return job
