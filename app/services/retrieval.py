from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.episode import Episode
from app.models.frame import Frame
from app.models.scene import Scene
from app.models.series import Series
from app.schemas.search import SearchHit, SearchImageResponse
from app.services.gemini import GeminiEmbeddingService

settings = get_settings()


class RetrievalService:
    def __init__(self) -> None:
        self.embedding_service = GeminiEmbeddingService()

    def search_image(self, db: Session, image_path: Path, limit: int = 3) -> SearchImageResponse:
        query_embedding = self.embedding_service.embed_image(image_path)

        scene_candidates = db.scalars(
            select(Scene)
            .where(Scene.embedding.isnot(None))
            .order_by(Scene.embedding.cosine_distance(query_embedding))
            .limit(settings.scene_top_k)
        ).all()

        hits: list[SearchHit] = []
        for scene in scene_candidates:
            frame_candidates = db.scalars(
                select(Frame)
                .where(Frame.scene_pk == scene.id, Frame.embedding.isnot(None))
                .order_by(Frame.embedding.cosine_distance(query_embedding))
                .limit(settings.frame_top_k)
            ).all()

            if not frame_candidates:
                continue

            best_frame = frame_candidates[0]
            episode = db.get(Episode, scene.episode_pk)
            series = db.get(Series, episode.series_pk) if episode else None
            score = self._rank(best_frame.context_asr_text, scene.summary or "")

            hits.append(
                SearchHit(
                    series_id=series.series_id if series else "",
                    episode_id=episode.episode_id if episode else "",
                    matched_ts=best_frame.frame_ts,
                    scene_start_ts=scene.start_ts,
                    scene_end_ts=scene.end_ts,
                    score=score,
                    scene_summary=scene.summary,
                    evidence_frames=[frame.image_path for frame in frame_candidates[:3]],
                    evidence_text=[scene.asr_text],
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        limited_hits = hits[:limit]
        low_confidence = (
            not limited_hits
            or limited_hits[0].score < settings.low_confidence_threshold
        )
        return SearchImageResponse(hits=limited_hits, low_confidence=low_confidence)

    def search_text(self, db: Session, query: str, limit: int = 3) -> SearchImageResponse:
        query_embedding = self.embedding_service.embed_text(query, task_type="RETRIEVAL_QUERY")

        scene_candidates = db.scalars(
            select(Scene)
            .where(Scene.embedding.isnot(None))
            .order_by(Scene.embedding.cosine_distance(query_embedding))
            .limit(settings.scene_top_k)
        ).all()

        hits: list[SearchHit] = []
        for scene in scene_candidates:
            episode = db.get(Episode, scene.episode_pk)
            series = db.get(Series, episode.series_pk) if episode else None
            score = self._rank(scene.asr_text, scene.summary or "")
            hits.append(
                SearchHit(
                    series_id=series.series_id if series else "",
                    episode_id=episode.episode_id if episode else "",
                    matched_ts=scene.start_ts,
                    scene_start_ts=scene.start_ts,
                    scene_end_ts=scene.end_ts,
                    score=score,
                    scene_summary=scene.summary,
                    evidence_frames=scene.representative_frame_paths[:3],
                    evidence_text=[scene.asr_text],
                )
            )
        hits.sort(key=lambda item: item.score, reverse=True)
        limited_hits = hits[:limit]
        low_confidence = (
            not limited_hits
            or limited_hits[0].score < settings.low_confidence_threshold
        )
        return SearchImageResponse(hits=limited_hits, low_confidence=low_confidence)

    @staticmethod
    def _rank(asr_text: str, summary: str) -> float:
        token_count = len(asr_text.split())
        summary_bonus = 0.05 if summary else 0.0
        return min(0.99, 0.3 + token_count / 1000 + summary_bonus)
