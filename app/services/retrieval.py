from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.episode import Episode
from app.models.segment import Segment
from app.models.series import Series
from app.schemas.search import SearchHit, SearchImageResponse
from app.services.gemini import GeminiEmbeddingService

settings = get_settings()


class RetrievalService:
    def __init__(self) -> None:
        self.embedding_service = GeminiEmbeddingService()

    def search_image(self, db: Session, image_path: Path, limit: int = 3) -> SearchImageResponse:
        query_embedding = self.embedding_service.embed_image(image_path)
        hits = self._search_segments(
            db=db,
            query_embedding=query_embedding,
            limit=limit,
        )
        return self._build_response(hits)

    def search_text(self, db: Session, query: str, limit: int = 3) -> SearchImageResponse:
        query_embedding = self.embedding_service.embed_text(query, task_type="RETRIEVAL_QUERY")
        hits = self._search_segments(
            db=db,
            query_embedding=query_embedding,
            limit=limit,
            text_query=query,
        )
        return self._build_response(hits)

    @staticmethod
    def _token_overlap(query: str, haystack: str) -> float:
        query_tokens = {token for token in query.lower().split() if token}
        haystack_tokens = {token for token in haystack.lower().split() if token}
        if not query_tokens or not haystack_tokens:
            return 0.0
        return len(query_tokens & haystack_tokens) / len(query_tokens)

    def _search_segments(
        self,
        db: Session,
        query_embedding: list[float],
        limit: int,
        text_query: str | None = None,
    ) -> list[SearchHit]:
        distance = Segment.embedding.cosine_distance(query_embedding)
        rows = db.execute(
            select(Segment, distance.label("distance"))
            .where(Segment.embedding.isnot(None))
            .order_by(distance)
            .limit(max(limit, settings.segment_top_k))
        ).all()

        hits: list[SearchHit] = []
        for segment, segment_distance in rows:
            episode = db.get(Episode, segment.episode_pk)
            series = db.get(Series, episode.series_pk) if episode else None
            overlap_bonus = 0.0
            if text_query:
                overlap_bonus = 0.15 * self._token_overlap(
                    text_query,
                    f"{segment.summary or ''} {segment.asr_text}",
                )

            score = max(
                0.0,
                min(0.99, 1 - float(segment_distance) / 2 + overlap_bonus),
            )
            hits.append(
                SearchHit(
                    series_id=series.series_id if series else "",
                    episode_id=episode.episode_id if episode else "",
                    matched_start_ts=segment.start_ts,
                    matched_end_ts=segment.end_ts,
                    score=score,
                    segment_summary=segment.summary,
                    evidence_images=segment.representative_frame_paths[:3],
                    evidence_text=[segment.asr_text],
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:limit]

    @staticmethod
    def _build_response(hits: list[SearchHit]) -> SearchImageResponse:
        low_confidence = not hits or hits[0].score < settings.low_confidence_threshold
        return SearchImageResponse(hits=hits, low_confidence=low_confidence)
