from __future__ import annotations

from pathlib import Path
from typing import Any


class ShotDetectionService:
    def detect_shots(self, video_path: Path) -> list[dict[str, Any]]:
        try:
            from scenedetect import SceneManager, open_video
            from scenedetect.detectors import ContentDetector
        except ImportError as exc:
            raise RuntimeError(
                "PySceneDetect is not installed. "
                "Install the 'pipeline' extra to enable shot detection."
            ) from exc

        video = open_video(str(video_path))
        manager = SceneManager()
        manager.add_detector(ContentDetector())
        manager.detect_scenes(video=video)

        scenes = []
        for index, (start, end) in enumerate(manager.get_scene_list()):
            scenes.append(
                {
                    "shot_index": index,
                    "start": start.get_seconds(),
                    "end": end.get_seconds(),
                }
            )
        return scenes
