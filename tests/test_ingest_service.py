from __future__ import annotations

from typing import cast

from sqlalchemy.orm import Session

from app.schemas.manifest import EpisodeManifest, SeriesManifest
from app.services.ingest import IngestService


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def all(self):
        return self._value


class FakeSession:
    def scalar(self, _query):
        return None

    def scalars(self, _query):
        return FakeScalarResult([])

    def execute(self, _query):
        raise AssertionError("execute should not run when no stored episodes exist")


def test_list_manifest_episodes_reads_manifest_without_syncing_db(monkeypatch) -> None:
    service = IngestService()
    manifest = SeriesManifest(
        series_id="example-series",
        series_title="示例剧",
        season_label="第一季",
        language="zh-CN",
        video_root="./videos",
        episodes=[
            EpisodeManifest(
                episode_id="ep01",
                episode_no=1,
                title="第一集",
                filename="01.mp4",
            )
        ],
    )

    monkeypatch.setattr(service.manifest_service, "load_manifest", lambda _path: manifest)
    monkeypatch.setattr(
        service.manifest_service,
        "sync_manifest",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("sync_manifest should not be called")
        ),
    )

    fake_db = FakeSession()
    summary, episodes = service.list_manifest_episodes(
        cast(Session, fake_db), "/repo/manifests/example.yaml"
    )

    assert summary.series_id == "example-series"
    assert len(episodes) == 1
    assert episodes[0].episode_id == "ep01"
    assert episodes[0].ingest_state == "not_ingested"
    assert episodes[0].frame_count == 0
