from __future__ import annotations

import json
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.episode import Episode
from app.models.series import Series
from app.schemas.manifest import EpisodeManifest, SeriesManifest


class ManifestError(ValueError):
    """Raised when a manifest is invalid or inconsistent with local files."""


class ManifestService:
    def load_manifest(self, manifest_path: str | Path) -> SeriesManifest:
        path = Path(manifest_path).expanduser().resolve()
        if not path.exists():
            raise ManifestError(f"manifest not found: {path}")

        if path.suffix.lower() in {".yaml", ".yml"}:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            raise ManifestError("manifest must be yaml, yml or json")

        manifest = SeriesManifest.model_validate(payload)
        self._validate_manifest(path, manifest)
        return manifest

    def _validate_manifest(self, manifest_path: Path, manifest: SeriesManifest) -> None:
        episode_ids = set()
        episode_numbers = set()
        video_root = (manifest_path.parent / manifest.video_root).resolve()
        if not video_root.exists():
            raise ManifestError(f"video_root does not exist: {video_root}")

        for episode in manifest.episodes:
            if episode.episode_id in episode_ids:
                raise ManifestError(f"duplicate episode_id: {episode.episode_id}")
            if episode.episode_no in episode_numbers:
                raise ManifestError(f"duplicate episode_no: {episode.episode_no}")

            episode_ids.add(episode.episode_id)
            episode_numbers.add(episode.episode_no)

            video_path = video_root / episode.filename
            if not video_path.exists():
                raise ManifestError(f"video file not found: {video_path}")

    def sync_manifest(self, db: Session, manifest_path: str | Path) -> Series:
        path = Path(manifest_path).expanduser().resolve()
        manifest = self.load_manifest(path)
        video_root = (path.parent / manifest.video_root).resolve()

        series = db.scalar(select(Series).where(Series.series_id == manifest.series_id))
        if series is None:
            series = Series(
                series_id=manifest.series_id,
                title=manifest.series_title,
                season_label=manifest.season_label,
                language=manifest.language,
                manifest_path=str(path),
            )
            db.add(series)
            db.flush()
        else:
            series.title = manifest.series_title
            series.season_label = manifest.season_label
            series.language = manifest.language
            series.manifest_path = str(path)

        existing = {
            episode.episode_id: episode
            for episode in db.scalars(select(Episode).where(Episode.series_pk == series.id)).all()
        }

        seen_episode_ids = set()
        for item in manifest.episodes:
            seen_episode_ids.add(item.episode_id)
            self._upsert_episode(db, series, item, video_root, existing.get(item.episode_id))

        for episode_id, episode in existing.items():
            if episode_id not in seen_episode_ids:
                db.delete(episode)

        db.flush()
        return series

    def get_episode_entry(self, manifest: SeriesManifest, episode_id: str) -> EpisodeManifest:
        for episode in manifest.episodes:
            if episode.episode_id == episode_id:
                return episode
        raise ManifestError(f"episode_id not found in manifest: {episode_id}")

    @staticmethod
    def resolve_video_path(
        manifest_path: str | Path, manifest: SeriesManifest, episode: EpisodeManifest
    ) -> Path:
        path = Path(manifest_path).expanduser().resolve()
        return (path.parent / manifest.video_root / episode.filename).resolve()

    def _upsert_episode(
        self,
        db: Session,
        series: Series,
        item: EpisodeManifest,
        video_root: Path,
        existing: Episode | None,
    ) -> Episode:
        video_path = str((video_root / item.filename).resolve())
        if existing is None:
            episode = Episode(
                series_pk=series.id,
                episode_id=item.episode_id,
                episode_no=item.episode_no,
                title=item.title,
                filename=item.filename,
                video_path=video_path,
            )
            db.add(episode)
            return episode

        existing.episode_no = item.episode_no
        existing.title = item.title
        existing.filename = item.filename
        existing.video_path = video_path
        return existing
