from __future__ import annotations

from pathlib import Path
from typing import Sequence, cast
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.episode import Episode
from app.models.frame import Frame
from app.models.series import Series
from app.services.gemini import GeminiConfigurationError
from app.services.retrieval import RetrievalService


class FakeResult:
    def __init__(self, rows: list[tuple[Frame, float]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Frame, float]]:
        return self._rows


class FakeScalarResult:
    def __init__(self, items: Sequence[object]) -> None:
        self._items = items

    def all(self) -> Sequence[object]:
        return self._items


class FakeSession:
    def __init__(
        self,
        *,
        frame_rows: list[tuple[Frame, float]] | None = None,
        frames: list[Frame] | None = None,
        objects: dict[tuple[type[object], object], object] | None = None,
    ) -> None:
        self._frame_rows = frame_rows or []
        self._frames = frames or []
        self._objects = objects or {}

    def execute(self, _statement: object) -> FakeResult:
        return FakeResult(self._frame_rows)

    def scalars(self, statement: object) -> FakeScalarResult:
        column_descriptions = getattr(statement, "column_descriptions", None)
        entity = column_descriptions[0].get("entity") if column_descriptions else None
        if entity is Frame:
            frames = self._frames
            for criterion in getattr(statement, "_where_criteria", ()):
                left = getattr(criterion, "left", None)
                right = getattr(criterion, "right", None)
                if getattr(left, "key", None) == "episode_pk":
                    episode_pk = getattr(right, "value", None)
                    frames = [frame for frame in frames if frame.episode_pk == episode_pk]
            return FakeScalarResult(frames)
        return FakeScalarResult(self._frames)

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
    frames = [
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=12.0,
            image_path="/tmp/frame_000000.jpg",
            context_asr_text="皇上驾到",
            raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
            embedding=None,
        ),
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=1,
            frame_ts=15.0,
            image_path="/tmp/frame_000001.jpg",
            context_asr_text="皇上驾到",
            raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
            embedding=None,
        ),
    ]
    db = FakeSession(
        frames=frames,
        objects={
            (Episode, episode.id): episode,
            (Series, series.id): series,
        },
    )

    response = RetrievalService().search_text(cast(Session, db), "皇上驾到", limit=3)

    assert response.low_confidence is False
    assert len(response.hits) == 1
    assert response.hits[0].series_label == "测试剧 S1"
    assert response.hits[0].episode_label == "第1集 · 第一集"
    assert response.hits[0].matched_start_ts == 12.0
    assert response.hits[0].matched_end_ts == 18.0
    assert response.hits[0].evidence_images == [
        "/tmp/frame_000000.jpg",
        "/tmp/frame_000001.jpg",
    ]


def test_search_text_handles_punctuation_and_typos_better() -> None:
    series, episode = build_series_and_episode()
    frames = [
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=12.0,
            image_path="/tmp/frame_000000.jpg",
            context_asr_text="皇上，驾到！",
            raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
            embedding=None,
        )
    ]
    db = FakeSession(
        frames=frames,
        objects={
            (Episode, episode.id): episode,
            (Series, series.id): series,
        },
    )

    response = RetrievalService().search_text(cast(Session, db), "皇上架到", limit=3)

    assert response.low_confidence is False
    assert len(response.hits) == 1
    assert response.hits[0].matched_start_ts == 12.0


def test_search_text_can_use_neighbor_context() -> None:
    series, episode = build_series_and_episode()
    frames = [
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=10.0,
            image_path="/tmp/frame_neighbor_0.jpg",
            context_asr_text="皇上",
            raw_metadata={"sample_interval_seconds": 2.0, "index_excluded": False},
            embedding=None,
        ),
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=1,
            frame_ts=12.0,
            image_path="/tmp/frame_neighbor_1.jpg",
            context_asr_text="驾到",
            raw_metadata={"sample_interval_seconds": 2.0, "index_excluded": False},
            embedding=None,
        ),
    ]
    db = FakeSession(
        frames=frames,
        objects={
            (Episode, episode.id): episode,
            (Series, series.id): series,
        },
    )

    response = RetrievalService().search_text(cast(Session, db), "皇上驾到", limit=3)

    assert response.low_confidence is False
    assert len(response.hits) >= 1
    assert response.hits[0].matched_start_ts == 10.0
    assert response.hits[0].matched_end_ts == 14.0


def test_search_text_returns_empty_images_when_no_frames_overlap() -> None:
    series, episode = build_series_and_episode()
    frames = [
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=12.0,
            image_path="/tmp/frame_000000.jpg",
            context_asr_text="皇上驾到",
            raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
            embedding=None,
        ),
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=30.0,
            image_path="/tmp/frame_000009.jpg",
            context_asr_text="无关帧",
            raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
            embedding=None,
        ),
    ]
    db = FakeSession(
        frames=frames,
        objects={(Episode, episode.id): episode, (Series, series.id): series},
    )

    response = RetrievalService().search_text(cast(Session, db), "皇上驾到", limit=3)

    assert len(response.hits) == 1
    assert response.hits[0].evidence_images == ["/tmp/frame_000000.jpg"]


def test_search_text_limits_evidence_images_to_five() -> None:
    series, episode = build_series_and_episode()
    frames = [
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=index,
            frame_ts=12.0 + index * 0.5,
            image_path=f"/tmp/frame_{index:06d}.jpg",
            context_asr_text="皇上驾到",
            raw_metadata={"sample_interval_seconds": 0.5, "index_excluded": False},
            embedding=None,
        )
        for index in range(7)
    ]
    db = FakeSession(
        frames=frames,
        objects={(Episode, episode.id): episode, (Series, series.id): series},
    )

    response = RetrievalService().search_text(cast(Session, db), "皇上驾到", limit=3)

    assert len(response.hits) == 1
    assert response.hits[0].evidence_images == [
        "/tmp/frame_000000.jpg",
        "/tmp/frame_000001.jpg",
        "/tmp/frame_000002.jpg",
        "/tmp/frame_000003.jpg",
        "/tmp/frame_000004.jpg",
    ]


def test_search_text_merged_hits_collect_images_from_merged_interval() -> None:
    series, episode = build_series_and_episode()
    frames = [
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=10.5,
            image_path="/tmp/frame_merged_1.jpg",
            context_asr_text="皇上",
            raw_metadata={"sample_interval_seconds": 1.0, "index_excluded": False},
            embedding=None,
        ),
        Frame(
            id=uuid4(),
            episode_pk=episode.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=1,
            frame_ts=15.5,
            image_path="/tmp/frame_merged_2.jpg",
            context_asr_text="驾到",
            raw_metadata={"sample_interval_seconds": 1.0, "index_excluded": False},
            embedding=None,
        ),
    ]
    db = FakeSession(
        frames=frames,
        objects={(Episode, episode.id): episode, (Series, series.id): series},
    )

    response = RetrievalService().search_text(cast(Session, db), "皇上驾到", limit=3)

    assert len(response.hits) == 1
    assert response.hits[0].matched_start_ts == 10.5
    assert response.hits[0].matched_end_ts == 16.5
    assert response.hits[0].evidence_images == [
        "/tmp/frame_merged_1.jpg",
        "/tmp/frame_merged_2.jpg",
    ]


def test_search_text_keeps_evidence_images_scoped_to_series_when_episode_ids_repeat() -> None:
    series_a = Series(
        id=uuid4(),
        series_id="series-a",
        title="A剧",
        season_label="S1",
        language="zh-CN",
        manifest_path="/tmp/a.yaml",
    )
    episode_a = Episode(
        id=uuid4(),
        series_pk=series_a.id,
        episode_id="ep01",
        episode_no=1,
        title="第一集",
        filename="a-ep01.mp4",
        video_path="/tmp/a-ep01.mp4",
    )
    series_b = Series(
        id=uuid4(),
        series_id="series-b",
        title="B剧",
        season_label="S1",
        language="zh-CN",
        manifest_path="/tmp/b.yaml",
    )
    episode_b = Episode(
        id=uuid4(),
        series_pk=series_b.id,
        episode_id="ep01",
        episode_no=1,
        title="第一集",
        filename="b-ep01.mp4",
        video_path="/tmp/b-ep01.mp4",
    )
    frames = [
        Frame(
            id=uuid4(),
            episode_pk=episode_a.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=12.0,
            image_path="/tmp/a-frame.jpg",
            context_asr_text="皇上驾到",
            raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
            embedding=None,
        ),
        Frame(
            id=uuid4(),
            episode_pk=episode_b.id,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=12.0,
            image_path="/tmp/b-frame.jpg",
            context_asr_text="皇上驾到",
            raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
            embedding=None,
        ),
    ]
    db = FakeSession(
        frames=frames,
        objects={
            (Episode, episode_a.id): episode_a,
            (Series, series_a.id): series_a,
            (Episode, episode_b.id): episode_b,
            (Series, series_b.id): series_b,
        },
    )

    response = RetrievalService().search_text(cast(Session, db), "皇上驾到", limit=2)

    assert len(response.hits) == 2
    evidence_images_by_series = {hit.series_id: hit.evidence_images for hit in response.hits}
    assert evidence_images_by_series == {
        "series-a": ["/tmp/a-frame.jpg"],
        "series-b": ["/tmp/b-frame.jpg"],
    }


def test_search_image_returns_low_confidence_when_gemini_is_unavailable() -> None:
    service = RetrievalService()

    def raise_missing_config(image_path: Path, task_type: str = "RETRIEVAL_QUERY") -> list[float]:
        del image_path, task_type
        raise GeminiConfigurationError("missing key")

    service.embedding_service.embed_image = raise_missing_config

    response = service.search_image(cast(Session, FakeSession()), Path("/tmp/query.jpg"))

    assert response.low_confidence is True
    assert response.hits == []


def test_search_image_returns_low_confidence_when_embeddings_are_missing() -> None:
    series, episode = build_series_and_episode()
    db = FakeSession(
        frame_rows=[],
        objects={(Episode, episode.id): episode, (Series, series.id): series},
    )
    service = RetrievalService()
    service.embedding_service.embed_image = lambda image_path, task_type="RETRIEVAL_QUERY": [
        0.1,
        0.2,
    ]

    response = service.search_image(cast(Session, db), Path("/tmp/query.jpg"), limit=3)

    assert response.low_confidence is True
    assert response.hits == []


def test_search_image_skips_excluded_frames_and_deduplicates_ranges() -> None:
    series, episode = build_series_and_episode()
    objects = {
        (Episode, episode.id): episode,
        (Series, series.id): series,
    }
    frame_rows = [
        (
            Frame(
                id=uuid4(),
                episode_pk=episode.id,
                shot_pk=None,
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
                shot_pk=None,
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
                shot_pk=None,
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
                shot_pk=None,
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
    service.embedding_service.embed_image = lambda image_path, task_type="RETRIEVAL_QUERY": [
        0.1,
        0.2,
    ]

    response = service.search_image(cast(Session, db), Path("/tmp/query.jpg"), limit=3)

    assert response.low_confidence is False
    assert [hit.matched_start_ts for hit in response.hits] == [3.0, 9.0]
    assert all(hit.matched_start_ts != 0.0 for hit in response.hits)


def test_search_text_falls_back_to_stable_identifiers_when_relations_are_missing() -> None:
    orphan_episode_pk = uuid4()
    frames = [
        Frame(
            id=uuid4(),
            episode_pk=orphan_episode_pk,
            shot_pk=None,
            scene_pk=None,
            frame_index=0,
            frame_ts=12.0,
            image_path="/tmp/frame_orphan.jpg",
            context_asr_text="皇上驾到",
            raw_metadata={"sample_interval_seconds": 3.0, "index_excluded": False},
            embedding=None,
        )
    ]
    db = FakeSession(frames=frames, objects={})

    response = RetrievalService().search_text(cast(Session, db), "皇上驾到", limit=1)

    assert len(response.hits) == 1
    assert response.hits[0].series_id == "未知剧集"
    assert response.hits[0].series_label == "未知剧集"
    assert response.hits[0].episode_id == str(orphan_episode_pk)
    assert response.hits[0].episode_label == str(orphan_episode_pk)
