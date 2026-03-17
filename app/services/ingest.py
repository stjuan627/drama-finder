from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.base import JobStage, JobStatus
from app.models.episode import Episode
from app.models.frame import Frame
from app.models.ingest_job import IngestJob
from app.models.scene import Scene
from app.models.series import Series
from app.models.shot import Shot
from app.schemas.ingest import IngestEpisodeRequest
from app.services.asr import ASRService
from app.services.gemini import GeminiEmbeddingService, SceneMergeService
from app.services.manifest import ManifestError, ManifestService
from app.services.media import FFmpegService
from app.services.queue import QueueService
from app.services.scene_detection import ShotDetectionService
from app.services.storage import StorageService

logger = logging.getLogger(__name__)
settings = get_settings()


class IngestService:
    def __init__(self) -> None:
        self.manifest_service = ManifestService()
        self.queue_service = QueueService()

    def submit(self, db: Session, payload: IngestEpisodeRequest) -> IngestJob:
        series = self.manifest_service.sync_manifest(db, payload.manifest_path)
        episode = db.scalar(
            select(Episode)
            .join(Series, Series.id == Episode.series_pk)
            .where(Series.series_id == payload.series_id, Episode.episode_id == payload.episode_id)
        )
        if episode is None:
            raise ManifestError("series_id or episode_id not found in manifest")

        existing = db.scalar(
            select(IngestJob)
            .where(IngestJob.series_pk == series.id, IngestJob.episode_pk == episode.id)
            .order_by(IngestJob.created_at.desc())
        )
        if existing and existing.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
            return existing

        job = IngestJob(
            series_pk=series.id,
            episode_pk=episode.id,
            manifest_path=str(Path(payload.manifest_path).expanduser().resolve()),
            status=JobStatus.QUEUED,
            current_stage=JobStage.MANIFEST,
            progress_current=0,
            progress_total=9,
            attempt=1 if existing is None else existing.attempt + 1,
            artifacts={},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        queue_id = self.queue_service.enqueue_ingest(str(job.id))
        job.artifacts = {**job.artifacts, "rq_job_id": queue_id}
        db.add(job)
        db.commit()
        db.refresh(job)
        return job


class IngestPipeline:
    def __init__(self) -> None:
        self.manifest_service = ManifestService()
        self.storage_service = StorageService()
        self.ffmpeg_service = FFmpegService()
        self.asr_service = ASRService()
        self.shot_service = ShotDetectionService()
        self.scene_merge_service = SceneMergeService()
        self.embedding_service = GeminiEmbeddingService()

    def run(self, db: Session, job_id: UUID | str) -> IngestJob:
        job = db.get(IngestJob, UUID(str(job_id)))
        if job is None:
            raise ValueError(f"job not found: {job_id}")

        episode = db.get(Episode, job.episode_pk)
        series = db.get(Series, job.series_pk)
        if episode is None or series is None:
            raise ValueError("job is missing linked series or episode")

        manifest = self.manifest_service.load_manifest(job.manifest_path)
        manifest_episode = self.manifest_service.get_episode_entry(
            manifest,
            episode.episode_id,
        )
        video_path = self.manifest_service.resolve_video_path(
            job.manifest_path,
            manifest,
            manifest_episode,
        )
        paths = self.storage_service.ensure_episode_paths(series.series_id, episode.episode_id)

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            db.commit()

            audio_path = paths.audio / "audio.wav"
            asr_path = paths.artifacts / "asr_segments.json"
            shots_path = paths.artifacts / "shots.json"
            scenes_path = paths.artifacts / "scenes.json"

            self._update_stage(db, job, JobStage.AUDIO_EXTRACTION, 1)
            if not audio_path.exists():
                self.ffmpeg_service.extract_audio(video_path, audio_path)

            self._update_stage(db, job, JobStage.ASR, 2)
            if asr_path.exists():
                asr_segments = self._load_json(asr_path)
            else:
                asr_segments = self.asr_service.transcribe(audio_path)
                asr_path.write_text(
                    json.dumps(asr_segments, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            self._update_stage(db, job, JobStage.SHOT_DETECTION, 3)
            if shots_path.exists():
                shots = self._load_json(shots_path)
            else:
                shots = self.shot_service.detect_shots(video_path)
                shots_path.write_text(
                    json.dumps(shots, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            self._update_stage(db, job, JobStage.FRAME_EXTRACTION, 4)
            frame_paths = sorted(paths.frames.glob("frame_*.jpg"))
            if not frame_paths:
                frame_paths = self.ffmpeg_service.extract_frames(video_path, paths.frames)

            self._update_stage(db, job, JobStage.REPRESENTATIVE_FRAMES, 5)
            shots = self._attach_representative_frames(shots, frame_paths)

            self._update_stage(db, job, JobStage.SCENE_MERGE, 6)
            scenes = self.scene_merge_service.merge(shots, asr_segments)
            scenes_path.write_text(
                json.dumps(scenes, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self._update_stage(db, job, JobStage.EMBEDDINGS, 7)
            self._replace_episode_artifacts(db, episode.id)
            persisted_scenes = self._persist_scenes(db, episode, shots, scenes, asr_segments)
            self._persist_frames(db, episode, frame_paths, persisted_scenes, asr_segments)

            self._update_stage(db, job, JobStage.PERSIST, 8)
            job.status = JobStatus.COMPLETED
            job.progress_current = job.progress_total
            job.finished_at = datetime.now(UTC)
            job.artifacts = {
                **job.artifacts,
                "audio_path": str(audio_path),
                "asr_segments_path": str(asr_path),
                "shots_path": str(shots_path),
                "scenes_path": str(scenes_path),
                "frame_count": len(frame_paths),
                "scene_count": len(persisted_scenes),
            }
            db.add(job)
            db.commit()
            db.refresh(job)
            return job
        except Exception as exc:
            logger.exception("ingest job failed: %s", job.id)
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.finished_at = datetime.now(UTC)
            db.add(job)
            db.commit()
            raise

    @staticmethod
    def _update_stage(db: Session, job: IngestJob, stage: JobStage, progress: int) -> None:
        job.current_stage = stage
        job.progress_current = progress
        db.add(job)
        db.commit()

    @staticmethod
    def _attach_representative_frames(shots: list[dict], frame_paths: list[Path]) -> list[dict]:
        for shot in shots:
            shot["representative_frame_paths"] = (
                [str(frame_paths[min(shot["shot_index"], len(frame_paths) - 1)])]
                if frame_paths
                else []
            )
        return shots

    @staticmethod
    def _replace_episode_artifacts(db: Session, episode_pk: UUID) -> None:
        db.execute(delete(Frame).where(Frame.episode_pk == episode_pk))
        db.execute(delete(Scene).where(Scene.episode_pk == episode_pk))
        db.execute(delete(Shot).where(Shot.episode_pk == episode_pk))
        db.commit()

    def _persist_scenes(
        self,
        db: Session,
        episode: Episode,
        shots: list[dict],
        scenes: list[dict],
        asr_segments: list[dict],
    ) -> list[Scene]:
        shot_by_index = {shot["shot_index"]: shot for shot in shots}
        persisted: list[Scene] = []

        for shot in shots:
            db.add(
                Shot(
                    episode_pk=episode.id,
                    shot_index=shot["shot_index"],
                    start_ts=shot["start"],
                    end_ts=shot["end"],
                    representative_frame_paths=shot.get("representative_frame_paths", []),
                    raw_metadata=shot,
                )
            )
        db.flush()

        for scene in scenes:
            scene_shots = [
                shot_by_index[index]
                for index in scene.get("shot_indexes", [])
                if index in shot_by_index
            ]
            if not scene_shots:
                continue

            asr_text = self._collect_asr_text(asr_segments, scene["start"], scene["end"])
            frame_paths = [
                frame_path
                for shot in scene_shots
                for frame_path in shot.get("representative_frame_paths", [])
            ]
            embedding = None
            if not settings.ingest_skip_embeddings:
                embedding = self.embedding_service.embed_multimodal(
                    text=f"{scene.get('summary', '')}\n{asr_text}".strip(),
                    image_paths=[Path(path) for path in frame_paths[:3]],
                )

            model = Scene(
                episode_pk=episode.id,
                scene_index=scene["scene_index"],
                start_ts=scene["start"],
                end_ts=scene["end"],
                summary=scene.get("summary", ""),
                asr_text=asr_text,
                representative_frame_paths=frame_paths[:3],
                raw_metadata=scene,
                embedding=embedding,
            )
            db.add(model)
            persisted.append(model)

        db.commit()
        return persisted

    def _persist_frames(
        self,
        db: Session,
        episode: Episode,
        frame_paths: list[Path],
        scenes: list[Scene],
        asr_segments: list[dict],
    ) -> None:
        for index, frame_path in enumerate(frame_paths):
            frame_ts = float(index)
            scene = self._match_scene(frame_ts, scenes)
            context_text = self._collect_asr_text(asr_segments, frame_ts - 5, frame_ts + 5)
            embedding = None
            if not settings.ingest_skip_embeddings:
                embedding = self.embedding_service.embed_multimodal(
                    text=context_text,
                    image_paths=[frame_path],
                    task_type="RETRIEVAL_DOCUMENT",
                )
            db.add(
                Frame(
                    episode_pk=episode.id,
                    scene_pk=scene.id if scene else None,
                    shot_pk=None,
                    frame_index=index,
                    frame_ts=frame_ts,
                    image_path=str(frame_path),
                    context_asr_text=context_text,
                    raw_metadata={},
                    embedding=embedding,
                )
            )
        db.commit()

    @staticmethod
    def _collect_asr_text(asr_segments: list[dict], start_ts: float, end_ts: float) -> str:
        fragments = []
        for segment in asr_segments:
            if segment["end"] < start_ts or segment["start"] > end_ts:
                continue
            fragments.append(segment["text"])
        return " ".join(fragment.strip() for fragment in fragments if fragment.strip())

    @staticmethod
    def _match_scene(frame_ts: float, scenes: list[Scene]) -> Scene | None:
        for scene in scenes:
            if scene.start_ts <= frame_ts <= scene.end_ts:
                return scene
        return None

    @staticmethod
    def _load_json(path: Path) -> list[dict]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"expected list payload in {path}, got {type(payload).__name__}")
        return payload
