from __future__ import annotations

import json
from pathlib import Path

from app.schemas.manifest import SeriesManifest
from app.services.manifest import ManifestService


def test_manifest_v1_can_parse() -> None:
    payload = {
        "version": "v1",
        "series_id": "test-series",
        "series_title": "测试剧",
        "season_label": "第一季",
        "language": "zh-CN",
        "video_root": "./videos",
        "intro_duration_seconds": 120,
        "outro_duration_seconds": 120,
        "episodes": [
            {
                "episode_id": "ep01",
                "episode_no": 1,
                "title": "第一集",
                "filename": "ep01.mp4",
            }
        ],
    }

    manifest = SeriesManifest.model_validate_json(json.dumps(payload, ensure_ascii=False))
    assert manifest.series_id == "test-series"
    assert manifest.intro_duration_seconds == 120
    assert manifest.outro_duration_seconds == 120
    assert manifest.episodes[0].episode_no == 1


def test_manifest_service_loads_repo_example_with_mixed_extensions() -> None:
    manifest_path = Path("manifests/example-series.yaml").resolve()

    manifest = ManifestService().load_manifest(manifest_path)

    assert manifest.series_id == "example-series"
    assert manifest.intro_duration_seconds == 120
    assert manifest.outro_duration_seconds == 120
    assert [episode.filename for episode in manifest.episodes] == [
        "01.mp4",
        "02.mp4",
        "03.mp4",
        "04.mkv",
    ]
