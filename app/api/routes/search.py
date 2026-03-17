from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.search import SearchImageResponse, SearchTextRequest
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/search", tags=["search"])
service = RetrievalService()


@router.post("/image", response_model=SearchImageResponse)
async def search_image(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
) -> SearchImageResponse:
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = Path(temp_file.name)

    try:
        return service.search_image(db, temp_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    finally:
        temp_path.unlink(missing_ok=True)


@router.post("/text", response_model=SearchImageResponse)
def search_text(
    payload: SearchTextRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SearchImageResponse:
    try:
        return service.search_text(db, payload.query, payload.limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
