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
    @staticmethod
    def data_root() -> Path:
        return settings.data_path

    def to_data_relative_path(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.data_root()))

    def resolve_data_path(self, raw_path: str | Path) -> Path:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate.resolve()
        return (self.data_root() / candidate).resolve()

    def ensure_episode_paths(self, series_id: str, episode_id: str) -> EpisodePaths:
        root = self.data_root() / "series" / series_id / episode_id
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
