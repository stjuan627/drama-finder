from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher
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
    def _normalize_text(text: str) -> str:
        normalized_chars: list[str] = []
        for char in text.lower():
            category = unicodedata.category(char)
            if category.startswith(("P", "Z", "C")):
                continue
            normalized_chars.append(char)
        return "".join(normalized_chars)

    @staticmethod
    def _ngram_set(text: str, size: int = 2) -> set[str]:
        normalized = RetrievalService._normalize_text(text)
        if len(normalized) < size:
            return {normalized} if normalized else set()
        return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}

    @staticmethod
    def _trigram_similarity(left: str, right: str) -> float:
        left_grams = RetrievalService._ngram_set(left, size=3)
        right_grams = RetrievalService._ngram_set(right, size=3)
        if not left_grams or not right_grams:
            return 0.0
        overlap = len(left_grams & right_grams)
        return 2 * overlap / (len(left_grams) + len(right_grams))

    def _text_overlap(self, query: str, haystack: str) -> float:
        query_ngrams = self._ngram_set(query)
        haystack_ngrams = self._ngram_set(haystack)
        if not query_ngrams or not haystack_ngrams:
            return 0.0
        return len(query_ngrams & haystack_ngrams) / len(query_ngrams)

    @staticmethod
    def _neighbor_text(index: int, texts: list[str]) -> str:
        window = texts[max(0, index - 1) : min(len(texts), index + 2)]
        return "".join(window)

    def _score_text_candidate(
        self,
        normalized_query: str,
        normalized_text: str,
        normalized_neighbor_text: str,
    ) -> float:
        substring_bonus = 0.0
        if normalized_query and normalized_query in normalized_text:
            substring_bonus += 0.45
        elif normalized_query and normalized_query in normalized_neighbor_text:
            substring_bonus += 0.25

        overlap_score = self._text_overlap(normalized_query, normalized_text)
        trigram_score = max(
            self._trigram_similarity(normalized_query, normalized_text),
            self._trigram_similarity(normalized_query, normalized_neighbor_text),
        )
        edit_similarity = max(
            SequenceMatcher(None, normalized_query, normalized_text).ratio(),
            SequenceMatcher(None, normalized_query, normalized_neighbor_text).ratio(),
        )
        return min(
            0.99,
            substring_bonus
            + overlap_score * 0.25
            + trigram_score * 0.35
            + edit_similarity * 0.4,
        )

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
        normalized_query = self._normalize_text(query)
        shot_texts = [str(shot.raw_metadata.get("asr_text", "")).strip() for shot in shots]

        for index, shot in enumerate(shots):
            asr_text = shot_texts[index]
            if not asr_text or shot.raw_metadata.get("index_excluded") is True:
                continue

            neighbor_text = self._neighbor_text(index, shot_texts)
            score = self._score_text_candidate(
                normalized_query=normalized_query,
                normalized_text=self._normalize_text(asr_text),
                normalized_neighbor_text=self._normalize_text(neighbor_text),
            )
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
