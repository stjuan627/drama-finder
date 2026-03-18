from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.models.episode import Episode
from app.models.frame import Frame
from app.models.series import Series
from app.models.shot import Shot
from app.services.gemini import GeminiConfigurationError
from app.services.retrieval import RetrievalService


class FakeResult:
    def __init__(self, rows: list[tuple[Frame, float]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Frame, float]]:
        return self._rows


class FakeScalarResult:
    def __init__(self, items: list[Shot]) -> None:
        self._items = items

    def all(self) -> list[Shot]:
        return self._items


class FakeSession:
    def __init__(
        self,
        *,
        frame_rows: list[tuple[Frame, float]] | None = None,
        shots: list[Shot] | None = None,
        objects: dict[tuple[type[object], object], object] | None = None,
    ) -> None:
        self._frame_rows = frame_rows or []
        self._shots = shots or []
        self._objects = objects or {}

    def execute(self, _statement: object) -> FakeResult:
        return FakeResult(self._frame_rows)

    def scalars(self, _statement: object) -> FakeScalarResult:
        return FakeScalarResult(self._shots)

    def get(self, model: type[object], key: object) -> object | None:
        return self._objects.get((model, key))


def build_series_and_episode() -> tuple[Series, Episode]:
    series = Series(
        id=uuid4(),
        series_id="test-series",
        title="测试剧",
        season_label="S1",
        language="zh-CN",
        manifest_path="/tmp/manifest.yaml",
    )
    episode = Episode(
        id=uuid4(),
        series_pk=series.id,
        episode_id="ep01",
        episode_no=1,
        title="第一集",
        filename="ep01.mp4",
        video_path="/tmp/ep01.mp4",
    )
    return series, episode


def test_search_text_returns_interval_hit() -> None:
    series, episode = build_series_and_episode()
    shot = Shot(
        id=uuid4(),
        episode_pk=episode.id,
        shot_index=1,
        start_ts=12.0,
        end_ts=18.0,
        representative_frame_paths=[],
        raw_metadata={"asr_text": "皇上驾到", "index_excluded": False},
    )
    db = FakeSession(
        shots=[shot],
        objects={
            (Episode, episode.id): episode,
            (Series, series.id): series,
        },
    )

    response = RetrievalService().search_text(db, "皇上驾到", limit=3)

    assert response.low_confidence is False
    assert len(response.hits) == 1
    assert response.hits[0].matched_start_ts == 12.0
    assert response.hits[0].matched_end_ts == 18.0
    assert response.hits[0].evidence_images == []


def test_search_image_returns_low_confidence_when_gemini_is_unavailable() -> None:
    service = RetrievalService()

    def raise_missing_config(_image_path: Path) -> list[float]:
        raise GeminiConfigurationError("missing key")

    service.embedding_service.embed_image = raise_missing_config

    response = service.search_image(FakeSession(), Path("/tmp/query.jpg"))

    assert response.low_confidence is True
    assert response.hits == []


def test_search_image_skips_excluded_frames_and_deduplicates_ranges() -> None:
    series, episode = build_series_and_episode()
    shot = Shot(
        id=uuid4(),
        episode_pk=episode.id,
        shot_index=1,
        start_ts=0.0,
        end_ts=30.0,
        representative_frame_paths=[],
        raw_metadata={"asr_text": "测试台词", "index_excluded": False},
    )
    objects = {
        (Episode, episode.id): episode,
        (Series, series.id): series,
    }
    frame_rows = [
        (
            Frame(
                id=uuid4(),
                episode_pk=episode.id,
                shot_pk=shot.id,
                scene_pk=None,
                frame_index=0,
                frame_ts=0.0,
                image_path="/tmp/frame_000000.jpg",
                context_asr_text="片头",
                raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": True},
                embedding=[0.1, 0.2],
            ),
            0.01,
        ),
        (
            Frame(
                id=uuid4(),
                episode_pk=episode.id,
                shot_pk=shot.id,
                scene_pk=None,
                frame_index=1,
                frame_ts=3.0,
                image_path="/tmp/frame_000001.jpg",
                context_asr_text="第一段",
                raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
                embedding=[0.1, 0.2],
            ),
            0.05,
        ),
        (
            Frame(
                id=uuid4(),
                episode_pk=episode.id,
                shot_pk=shot.id,
                scene_pk=None,
                frame_index=2,
                frame_ts=5.0,
                image_path="/tmp/frame_000002.jpg",
                context_asr_text="重复候选",
                raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
                embedding=[0.1, 0.2],
            ),
            0.06,
        ),
        (
            Frame(
                id=uuid4(),
                episode_pk=episode.id,
                shot_pk=shot.id,
                scene_pk=None,
                frame_index=3,
                frame_ts=9.0,
                image_path="/tmp/frame_000003.jpg",
                context_asr_text="第二段",
                raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
                embedding=[0.1, 0.2],
            ),
            0.12,
        ),
    ]
    db = FakeSession(frame_rows=frame_rows, objects=objects)
    service = RetrievalService()
    service.embedding_service.embed_image = lambda _image_path: [0.1, 0.2]

    response = service.search_image(db, Path("/tmp/query.jpg"), limit=3)

    assert response.low_confidence is False
    assert [hit.matched_start_ts for hit in response.hits] == [3.0, 9.0]
    assert all(hit.matched_start_ts != 0.0 for hit in response.hits)
