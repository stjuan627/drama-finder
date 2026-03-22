from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.episode import Episode
from app.models.frame import Frame
from app.models.series import Series
from app.schemas.search import SearchHit, SearchImageResponse
from app.services.gemini import GeminiConfigurationError, GeminiEmbeddingService
from app.services.storage import StorageService

settings = get_settings()
EpisodeLookupKey = tuple[str, str]


class RetrievalService:
    def __init__(self) -> None:
        self.embedding_service = GeminiEmbeddingService()
        self.storage_service = StorageService()

    def _normalize_evidence_image_path(self, raw_path: str) -> str:
        resolved = self.storage_service.resolve_data_path(raw_path)
        try:
            return self.storage_service.to_data_relative_path(resolved)
        except ValueError:
            return raw_path

    @staticmethod
    def _series_label(series: Series | None, series_id: str) -> str:
        if series is None:
            return series_id or "未知剧集"

        title = series.title.strip()
        season_label = (series.season_label or "").strip()
        if title and season_label and season_label not in title:
            return f"{title} {season_label}"
        if title:
            return title
        if season_label:
            return f"{series_id} {season_label}".strip()
        return series_id

    @staticmethod
    def _episode_label(episode: Episode | None, fallback_id: str) -> str:
        if episode is None:
            return fallback_id or "未知剧集"

        parts: list[str] = []
        if episode.episode_no:
            parts.append(f"第{episode.episode_no}集")

        title = episode.title.strip()
        if title and title not in parts:
            parts.append(title)

        if parts:
            return " · ".join(parts)
        return fallback_id or episode.episode_id

    def search_image(self, db: Session, image_path: Path, limit: int = 3) -> SearchImageResponse:
        try:
            query_embedding = self.embedding_service.embed_image(image_path)
        except GeminiConfigurationError:
            return self._build_response([])
        hits = self._search_frames(db=db, query_embedding=query_embedding, limit=limit)
        return self._build_response(hits)

    def search_text(self, db: Session, query: str, limit: int = 3) -> SearchImageResponse:
        hits = self._search_frames_by_text(db=db, query=query, limit=limit)
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

    @staticmethod
    def _neighbor_frame_text(
        index: int, frames: Sequence[Frame], max_gap_seconds: float = 6.0
    ) -> str:
        current = frames[index]
        window = [current.context_asr_text]

        previous_index = index - 1
        if previous_index >= 0:
            previous = frames[previous_index]
            if (
                previous.episode_pk == current.episode_pk
                and current.frame_ts - previous.frame_ts <= max_gap_seconds
            ):
                window.insert(0, previous.context_asr_text)

        next_index = index + 1
        if next_index < len(frames):
            following = frames[next_index]
            if (
                following.episode_pk == current.episode_pk
                and following.frame_ts - current.frame_ts <= max_gap_seconds
            ):
                window.append(following.context_asr_text)

        return "".join(text.strip() for text in window if text.strip())

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
            substring_bonus + overlap_score * 0.25 + trigram_score * 0.35 + edit_similarity * 0.4,
        )

    @staticmethod
    def _merge_nearby_hits(hits: list[SearchHit], gap_seconds: float = 6.0) -> list[SearchHit]:
        if not hits:
            return []

        sorted_hits = sorted(
            hits,
            key=lambda item: (item.series_id, item.episode_id, item.matched_start_ts, -item.score),
        )
        merged: list[SearchHit] = []

        for hit in sorted_hits:
            if not merged:
                merged.append(hit)
                continue

            previous = merged[-1]
            same_episode = (
                previous.series_id == hit.series_id and previous.episode_id == hit.episode_id
            )
            close_enough = hit.matched_start_ts <= previous.matched_end_ts + gap_seconds
            if same_episode and close_enough:
                merged[-1] = SearchHit(
                    series_id=previous.series_id,
                    episode_id=previous.episode_id,
                    series_label=previous.series_label,
                    episode_label=previous.episode_label,
                    matched_start_ts=min(previous.matched_start_ts, hit.matched_start_ts),
                    matched_end_ts=max(previous.matched_end_ts, hit.matched_end_ts),
                    score=max(previous.score, hit.score),
                    evidence_images=[],
                    evidence_text=list(dict.fromkeys(previous.evidence_text + hit.evidence_text)),
                )
            else:
                merged.append(hit)

        merged.sort(key=lambda item: item.score, reverse=True)
        return merged

    @staticmethod
    def _frame_interval(frame: Frame) -> tuple[float, float]:
        interval = float(
            frame.raw_metadata.get("sample_interval_seconds", settings.frame_index_interval_seconds)
        )
        start_ts = frame.frame_ts
        end_ts = frame.frame_ts + interval
        return start_ts, end_ts

    @classmethod
    def _frame_overlaps_hit(cls, frame: Frame, start_ts: float, end_ts: float) -> bool:
        frame_start_ts, frame_end_ts = cls._frame_interval(frame)
        return frame_start_ts < end_ts and frame_end_ts > start_ts

    def _select_evidence_images(self, frames: list[Frame], max_images: int = 5) -> list[str]:
        selected: list[str] = []
        seen_paths: set[str] = set()
        ordered_frames = sorted(
            frames,
            key=lambda frame: (frame.frame_ts, frame.frame_index, frame.image_path),
        )
        for frame in ordered_frames:
            if frame.raw_metadata.get("index_excluded") is True:
                continue
            normalized_path = self._normalize_evidence_image_path(frame.image_path)
            if normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)
            selected.append(normalized_path)
            if len(selected) >= max_images:
                break
        return selected

    def _load_frames_for_text_hit(
        self,
        db: Session,
        episode_pk: object,
        start_ts: float,
        end_ts: float,
    ) -> list[Frame]:
        frames = db.scalars(
            select(Frame)
            .where(Frame.episode_pk == episode_pk)
            .order_by(Frame.frame_ts.asc(), Frame.frame_index.asc())
        ).all()
        return [
            frame
            for frame in frames
            if self._frame_overlaps_hit(frame, start_ts=start_ts, end_ts=end_ts)
        ]

    def _attach_evidence_images_to_text_hits(
        self,
        db: Session,
        hits: list[SearchHit],
        episode_pks: dict[EpisodeLookupKey, object],
        max_images: int = 5,
    ) -> list[SearchHit]:
        attached_hits: list[SearchHit] = []
        for hit in hits:
            episode_pk = episode_pks.get((hit.series_id, hit.episode_id))
            evidence_images: list[str] = []
            if episode_pk is not None:
                frames = self._load_frames_for_text_hit(
                    db,
                    episode_pk=episode_pk,
                    start_ts=hit.matched_start_ts,
                    end_ts=hit.matched_end_ts,
                )
                evidence_images = self._select_evidence_images(frames, max_images=max_images)
            attached_hits.append(
                SearchHit(
                    series_id=hit.series_id,
                    episode_id=hit.episode_id,
                    series_label=hit.series_label,
                    episode_label=hit.episode_label,
                    matched_start_ts=hit.matched_start_ts,
                    matched_end_ts=hit.matched_end_ts,
                    score=hit.score,
                    evidence_images=evidence_images,
                    evidence_text=hit.evidence_text,
                )
            )
        return attached_hits

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
                series.series_id if series else (str(episode.series_pk) if episode else "未知剧集"),
                episode.episode_id if episode else str(frame.episode_pk),
            )
            series_label = self._series_label(series, key[0])
            episode_label = self._episode_label(episode, key[1])
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
                    series_label=series_label,
                    episode_label=episode_label,
                    matched_start_ts=start_ts,
                    matched_end_ts=end_ts,
                    score=score,
                    evidence_images=[self._normalize_evidence_image_path(frame.image_path)],
                    evidence_text=[frame.context_asr_text] if frame.context_asr_text else [],
                )
            )
            selected_ranges.setdefault(key, []).append((start_ts, end_ts))
            if len(hits) >= limit:
                break

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:limit]

    def _search_frames_by_text(
        self,
        db: Session,
        query: str,
        limit: int,
    ) -> list[SearchHit]:
        frames = db.scalars(
            select(Frame).order_by(Frame.episode_pk, Frame.frame_ts, Frame.frame_index)
        ).all()
        ranked: list[tuple[float, Frame]] = []
        normalized_query = self._normalize_text(query)
        frame_texts = [frame.context_asr_text.strip() for frame in frames]

        for index, frame in enumerate(frames):
            asr_text = frame_texts[index]
            if not asr_text or frame.raw_metadata.get("index_excluded") is True:
                continue

            neighbor_text = self._neighbor_frame_text(index, frames)
            score = self._score_text_candidate(
                normalized_query=normalized_query,
                normalized_text=self._normalize_text(asr_text),
                normalized_neighbor_text=self._normalize_text(neighbor_text),
            )
            if score <= 0:
                continue
            ranked.append((min(0.99, score), frame))

        ranked.sort(key=lambda item: item[0], reverse=True)

        hits: list[SearchHit] = []
        episode_pks: dict[EpisodeLookupKey, object] = {}
        for score, frame in ranked[: max(limit, settings.text_search_top_k)]:
            episode = db.get(Episode, frame.episode_pk)
            series = db.get(Series, episode.series_pk) if episode else None
            series_id = (
                series.series_id if series else (str(episode.series_pk) if episode else "未知剧集")
            )
            episode_id = episode.episode_id if episode else str(frame.episode_pk)
            series_label = self._series_label(series, series_id)
            episode_label = self._episode_label(episode, episode_id)
            if episode is not None:
                episode_pks[(series_id, episode_id)] = episode.id
            start_ts, end_ts = self._frame_interval(frame)
            hits.append(
                SearchHit(
                    series_id=series_id,
                    episode_id=episode_id,
                    series_label=series_label,
                    episode_label=episode_label,
                    matched_start_ts=start_ts,
                    matched_end_ts=end_ts,
                    score=score,
                    evidence_images=[],
                    evidence_text=[frame.context_asr_text],
                )
            )

        merged_hits = self._merge_nearby_hits(hits)
        limited_hits = merged_hits[:limit]
        return self._attach_evidence_images_to_text_hits(db, limited_hits, episode_pks)

    @staticmethod
    def _build_response(hits: list[SearchHit]) -> SearchImageResponse:
        low_confidence = not hits or hits[0].score < settings.low_confidence_threshold
        return SearchImageResponse(hits=hits, low_confidence=low_confidence)
