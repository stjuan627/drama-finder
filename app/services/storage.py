from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


@dataclass(slots=True)
class EpisodePaths:
    root: Path
    source: Path
    audio: Path
    frames: Path
    artifacts: Path


class StorageService:
    def ensure_episode_paths(self, series_id: str, episode_id: str) -> EpisodePaths:
        root = settings.data_path / "series" / series_id / episode_id
        paths = EpisodePaths(
            root=root,
            source=root / "source",
            audio=root / "audio",
            frames=root / "frames",
            artifacts=root / "artifacts",
        )
        for path in (paths.root, paths.source, paths.audio, paths.frames, paths.artifacts):
            path.mkdir(parents=True, exist_ok=True)
        return paths
