from pathlib import Path

from app.services.ingest import IngestPipeline
from app.services.storage import StorageService


def test_manifest_intro_outro_ranges_do_not_shift_timeline() -> None:
    ranges = IngestPipeline._build_excluded_ranges(
        duration_seconds=1800.0,
        intro_seconds=120.0,
        outro_seconds=120.0,
    )

    assert ranges == [
        {"start": 0.0, "end": 120.0},
        {"start": 1680.0, "end": 1800.0},
    ]


def test_overlap_detection_marks_intro_and_outro_windows() -> None:
    ranges = [
        {"start": 0.0, "end": 120.0},
        {"start": 1680.0, "end": 1800.0},
    ]

    assert IngestPipeline._overlaps_excluded_range(30.0, 40.0, ranges) is True
    assert IngestPipeline._overlaps_excluded_range(300.0, 330.0, ranges) is False
    assert IngestPipeline._overlaps_excluded_range(1750.0, 1760.0, ranges) is True


def test_storage_service_round_trips_data_relative_paths(tmp_path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    frame_path = data_root / "series" / "demo" / "ep01" / "frames" / "frame_000001.jpg"

    monkeypatch.setattr(
        StorageService,
        "data_root",
        staticmethod(lambda: data_root.resolve()),
    )

    service = StorageService()

    assert service.to_data_relative_path(frame_path) == str(
        Path("series") / "demo" / "ep01" / "frames" / "frame_000001.jpg"
    )
    assert (
        service.resolve_data_path("series/demo/ep01/frames/frame_000001.jpg")
        == frame_path.resolve()
    )
    assert service.resolve_data_path(frame_path.resolve()) == frame_path.resolve()
