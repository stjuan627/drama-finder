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
from app.models.series import Series
from app.models.shot import Shot
from app.schemas.ingest import IngestEpisodeRequest
from app.services.asr import ASRService
from app.services.gemini import GeminiEmbeddingService
from app.services.manifest import ManifestError, ManifestService
from app.services.media import FFmpegService
from app.services.queue import QueueService
from app.services.scene_detection import ShotDetectionService
from app.services.storage import StorageService

logger = logging.getLogger(__name__)
settings = get_settings()
FRAME_INDEX_INTERVAL_SECONDS = 3.0


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
            progress_total=6,
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
        duration_seconds = self.ffmpeg_service.probe_duration(video_path)
        excluded_ranges = self._build_excluded_ranges(
            duration_seconds=duration_seconds,
            intro_seconds=manifest.intro_duration_seconds,
            outro_seconds=manifest.outro_duration_seconds,
        )
        paths = self.storage_service.ensure_episode_paths(series.series_id, episode.episode_id)

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            db.commit()

            audio_path = paths.audio / "audio.wav"
            asr_path = paths.artifacts / "asr_segments.json"
            shots_path = paths.artifacts / "shots.json"
            frames_manifest_path = paths.artifacts / "indexed_frames.json"

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

            self._remove_legacy_shot_frames(paths.frames)

            self._update_stage(db, job, JobStage.FRAME_EXTRACTION, 4)
            frame_paths = self.ffmpeg_service.extract_frames(
                video_path,
                paths.frames,
                fps=f"1/{FRAME_INDEX_INTERVAL_SECONDS:g}",
            )
            frames_manifest_path.write_text(
                json.dumps(
                    self._build_frame_manifest(frame_paths, FRAME_INDEX_INTERVAL_SECONDS),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self._update_stage(db, job, JobStage.EMBEDDINGS, 5)
            self._replace_episode_artifacts(db, episode.id)
            persisted_shots = self._persist_shots(
                db=db,
                episode=episode,
                shots=shots,
                asr_segments=asr_segments,
                excluded_ranges=excluded_ranges,
            )
            persisted_frames = self._persist_frames(
                db=db,
                episode=episode,
                shots=persisted_shots,
                frame_paths=frame_paths,
                asr_segments=asr_segments,
                excluded_ranges=excluded_ranges,
                duration_seconds=duration_seconds,
            )
            pending_frame_embeddings = sum(
                1 for frame in persisted_frames if self._frame_needs_embedding(frame)
            )

            self._update_stage(db, job, JobStage.PERSIST, 6)
            job.status = JobStatus.COMPLETED
            job.progress_current = job.progress_total
            job.finished_at = datetime.now(UTC)
            job.artifacts = {
                **job.artifacts,
                "audio_path": str(audio_path),
                "asr_segments_path": str(asr_path),
                "shots_path": str(shots_path),
                "indexed_frames_path": str(frames_manifest_path),
                "shot_count": len(persisted_shots),
                "frame_count": len(persisted_frames),
                "index_excluded_ranges": excluded_ranges,
                "frame_index_interval_seconds": FRAME_INDEX_INTERVAL_SECONDS,
                "embedding_mode": "deferred",
                "pending_frame_embeddings": pending_frame_embeddings,
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
    def _remove_legacy_shot_frames(frames_dir: Path) -> None:
        for output_path in frames_dir.glob("shot_*.jpg"):
            output_path.unlink(missing_ok=True)

    @staticmethod
    def _replace_episode_artifacts(db: Session, episode_pk: UUID) -> None:
        db.execute(delete(Frame).where(Frame.episode_pk == episode_pk))
        db.execute(delete(Shot).where(Shot.episode_pk == episode_pk))
        db.commit()

    def _persist_shots(
        self,
        db: Session,
        episode: Episode,
        shots: list[dict],
        asr_segments: list[dict],
        excluded_ranges: list[dict[str, float]],
    ) -> list[Shot]:
        persisted: list[Shot] = []
        for shot in shots:
            start_ts = float(shot["start"])
            end_ts = float(shot["end"])
            asr_text = self._collect_asr_text(asr_segments, start_ts, end_ts)
            model = Shot(
                episode_pk=episode.id,
                shot_index=shot["shot_index"],
                start_ts=start_ts,
                end_ts=end_ts,
                representative_frame_paths=[],
                raw_metadata={
                    **shot,
                    "asr_text": asr_text,
                    "index_excluded": self._overlaps_excluded_range(
                        start_ts,
                        end_ts,
                        excluded_ranges,
                    ),
                },
            )
            db.add(model)
            persisted.append(model)

        db.flush()
        return persisted

    def _persist_frames(
        self,
        db: Session,
        episode: Episode,
        shots: list[Shot],
        frame_paths: list[Path],
        asr_segments: list[dict],
        excluded_ranges: list[dict[str, float]],
        duration_seconds: float,
    ) -> list[Frame]:
        persisted: list[Frame] = []
        interval = FRAME_INDEX_INTERVAL_SECONDS
        for index, frame_path in enumerate(frame_paths):
            frame_ts = round(index * interval, 3)
            if frame_ts > duration_seconds:
                break

            matched_shot = self._match_shot(frame_ts, shots)
            context_text = self._collect_asr_text(
                asr_segments,
                max(0.0, frame_ts - settings.asr_context_window_seconds),
                frame_ts + settings.asr_context_window_seconds,
            )
            index_excluded = self._overlaps_excluded_range(
                frame_ts,
                min(duration_seconds, frame_ts + interval),
                excluded_ranges,
            )

            model = Frame(
                episode_pk=episode.id,
                shot_pk=matched_shot.id if matched_shot else None,
                scene_pk=None,
                frame_index=index,
                frame_ts=frame_ts,
                image_path=str(frame_path),
                context_asr_text=context_text,
                raw_metadata={
                    "index_excluded": index_excluded,
                    "sample_interval_seconds": interval,
                    "embedding_status": (
                        "skipped_index_excluded" if index_excluded else "pending_backfill"
                    ),
                },
                embedding=None,
            )
            db.add(model)
            persisted.append(model)

        db.commit()
        return persisted

    def backfill_frame_embeddings(
        self,
        db: Session,
        episode_pk: UUID | str,
        limit: int | None = None,
    ) -> dict[str, int]:
        target_episode_pk = UUID(str(episode_pk))
        rows = db.scalars(
            select(Frame)
            .where(Frame.episode_pk == target_episode_pk)
            .order_by(Frame.frame_index.asc())
        ).all()
        pending_frames = [frame for frame in rows if self._frame_needs_embedding(frame)]
        if limit is not None:
            pending_frames = pending_frames[: max(0, limit)]

        updated = 0
        failed = 0
        for frame in pending_frames:
            metadata = dict(frame.raw_metadata or {})
            try:
                frame.embedding = self.embedding_service.embed_frame_document(
                    image_path=Path(frame.image_path),
                    context_text=frame.context_asr_text,
                )
                metadata["embedding_status"] = "ready"
                updated += 1
            except Exception as exc:
                metadata["embedding_status"] = "failed"
                metadata["embedding_error"] = str(exc)
                failed += 1
                logger.exception("frame embedding backfill failed: frame_id=%s", frame.id)
            frame.raw_metadata = metadata
            db.add(frame)

        db.commit()
        return {
            "pending": len(pending_frames),
            "updated": updated,
            "failed": failed,
        }

    @staticmethod
    def _build_frame_manifest(
        frame_paths: list[Path],
        interval_seconds: float,
    ) -> list[dict[str, float | str]]:
        return [
            {
                "frame_index": index,
                "frame_ts": round(index * interval_seconds, 3),
                "image_path": str(frame_path),
            }
            for index, frame_path in enumerate(frame_paths)
        ]

    @staticmethod
    def _collect_asr_text(asr_segments: list[dict], start_ts: float, end_ts: float) -> str:
        fragments = []
        for segment in asr_segments:
            if segment["end"] < start_ts or segment["start"] > end_ts:
                continue
            fragments.append(segment["text"])
        return " ".join(fragment.strip() for fragment in fragments if fragment.strip())

    @staticmethod
    def _build_excluded_ranges(
        duration_seconds: float,
        intro_seconds: float,
        outro_seconds: float,
    ) -> list[dict[str, float]]:
        ranges: list[dict[str, float]] = []
        if intro_seconds > 0:
            ranges.append({"start": 0.0, "end": min(duration_seconds, float(intro_seconds))})
        if outro_seconds > 0:
            start_ts = max(0.0, duration_seconds - float(outro_seconds))
            ranges.append({"start": start_ts, "end": duration_seconds})
        return [item for item in ranges if item["end"] > item["start"]]

    @staticmethod
    def _overlaps_excluded_range(
        start_ts: float,
        end_ts: float,
        excluded_ranges: list[dict[str, float]],
    ) -> bool:
        return any(
            end_ts > excluded_range["start"] and start_ts < excluded_range["end"]
            for excluded_range in excluded_ranges
        )

    @staticmethod
    def _match_shot(frame_ts: float, shots: list[Shot]) -> Shot | None:
        for shot in shots:
            if shot.start_ts <= frame_ts <= shot.end_ts:
                return shot
        return None

    @staticmethod
    def _load_json(path: Path) -> list[dict]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"expected list payload in {path}, got {type(payload).__name__}")
        return payload

    @staticmethod
    def _frame_needs_embedding(frame: Frame) -> bool:
        metadata = frame.raw_metadata or {}
        return frame.embedding is None and metadata.get("index_excluded") is not True
