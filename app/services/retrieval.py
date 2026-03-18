from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.episode import Episode
from app.models.frame import Frame
from app.models.series import Series
from app.models.shot import Shot
from app.schemas.search import SearchHit, SearchImageResponse
from app.services.gemini import GeminiConfigurationError, GeminiEmbeddingService

settings = get_settings()


class RetrievalService:
    def __init__(self) -> None:
        self.embedding_service = GeminiEmbeddingService()

    def search_image(self, db: Session, image_path: Path, limit: int = 3) -> SearchImageResponse:
        try:
            query_embedding = self.embedding_service.embed_image(image_path)
        except GeminiConfigurationError:
            return self._build_response([])
        hits = self._search_frames(db=db, query_embedding=query_embedding, limit=limit)
        return self._build_response(hits)

    def search_text(self, db: Session, query: str, limit: int = 3) -> SearchImageResponse:
        hits = self._search_shots(db=db, query=query, limit=limit)
        return self._build_response(hits)

    @staticmethod
    def _ngram_set(text: str, size: int = 2) -> set[str]:
        normalized = "".join(text.lower().split())
        if len(normalized) < size:
            return {normalized} if normalized else set()
        return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}

    def _text_overlap(self, query: str, haystack: str) -> float:
        query_ngrams = self._ngram_set(query)
        haystack_ngrams = self._ngram_set(haystack)
        if not query_ngrams or not haystack_ngrams:
            return 0.0
        return len(query_ngrams & haystack_ngrams) / len(query_ngrams)

    def _search_frames(
        self,
        db: Session,
        query_embedding: list[float],
        limit: int,
    ) -> list[SearchHit]:
        distance = Frame.embedding.cosine_distance(query_embedding)
        rows = db.execute(
            select(Frame, distance.label("distance"))
            .where(Frame.embedding.isnot(None))
            .order_by(distance)
            .limit(max(limit, settings.image_search_top_k))
        ).all()

        hits: list[SearchHit] = []
        selected_ranges: dict[tuple[str, str], list[tuple[float, float]]] = {}
        for frame, frame_distance in rows:
            if frame.raw_metadata.get("index_excluded") is True:
                continue

            episode = db.get(Episode, frame.episode_pk)
            series = db.get(Series, episode.series_pk) if episode else None
            interval = float(frame.raw_metadata.get("sample_interval_seconds", 3.0))
            key = (
                series.series_id if series else "",
                episode.episode_id if episode else "",
            )
            start_ts = frame.frame_ts
            end_ts = frame.frame_ts + interval
            existing_ranges = selected_ranges.get(key, [])
            overlaps_existing_range = any(
                start_ts < existing_end and end_ts > existing_start
                for existing_start, existing_end in existing_ranges
            )
            if overlaps_existing_range:
                continue

            score = max(
                0.0,
                min(0.99, 1 - float(frame_distance) / 2),
            )
            hits.append(
                SearchHit(
                    series_id=key[0],
                    episode_id=key[1],
                    matched_start_ts=start_ts,
                    matched_end_ts=end_ts,
                    score=score,
                    evidence_images=[frame.image_path],
                    evidence_text=[frame.context_asr_text] if frame.context_asr_text else [],
                )
            )
            selected_ranges.setdefault(key, []).append((start_ts, end_ts))
            if len(hits) >= limit:
                break

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:limit]

    def _search_shots(
        self,
        db: Session,
        query: str,
        limit: int,
    ) -> list[SearchHit]:
        shots = db.scalars(select(Shot).order_by(Shot.start_ts)).all()
        ranked: list[tuple[float, Shot]] = []
        normalized_query = "".join(query.split())

        for shot in shots:
            asr_text = str(shot.raw_metadata.get("asr_text", "")).strip()
            if not asr_text or shot.raw_metadata.get("index_excluded") is True:
                continue

            score = self._text_overlap(normalized_query, asr_text)
            if normalized_query and normalized_query in "".join(asr_text.split()):
                score += 0.35
            if score <= 0:
                continue
            ranked.append((min(0.99, score), shot))

        ranked.sort(key=lambda item: item[0], reverse=True)

        hits: list[SearchHit] = []
        for score, shot in ranked[: max(limit, settings.text_search_top_k)]:
            episode = db.get(Episode, shot.episode_pk)
            series = db.get(Series, episode.series_pk) if episode else None
            hits.append(
                SearchHit(
                    series_id=series.series_id if series else "",
                    episode_id=episode.episode_id if episode else "",
                    matched_start_ts=shot.start_ts,
                    matched_end_ts=shot.end_ts,
                    score=score,
                    evidence_images=[],
                    evidence_text=[str(shot.raw_metadata.get("asr_text", ""))],
                )
            )

        return hits[:limit]

    @staticmethod
    def _build_response(hits: list[SearchHit]) -> SearchImageResponse:
        low_confidence = not hits or hits[0].score < settings.low_confidence_threshold
        return SearchImageResponse(hits=hits, low_confidence=low_confidence)
