from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient

from app.api.routes import ingest as ingest_routes
from app.main import app
from app.models.base import JobStage, JobStatus
from app.schemas.ingest import EpisodeIngestStatusRead, ManifestSummaryRead
from app.services.manifest import ManifestError


client = TestClient(app)


def override_db() -> Generator[object, None, None]:
    yield object()


def test_list_manifests_returns_discovered_manifest_summaries(monkeypatch) -> None:
    expected = [
        ManifestSummaryRead(
            manifest_path="/repo/manifests/example-series.yaml",
            series_id="example-series",
            series_title="示例剧",
            season_label="第一季",
            language="zh-CN",
            episode_count=4,
        )
    ]
    monkeypatch.setattr(ingest_routes.service, "list_manifests", lambda: expected)

    response = client.get("/ingest/manifests")

    assert response.status_code == 200
    assert response.json() == [
        {
            "manifest_path": "/repo/manifests/example-series.yaml",
            "series_id": "example-series",
            "series_title": "示例剧",
            "season_label": "第一季",
            "language": "zh-CN",
            "episode_count": 4,
        }
    ]


def test_list_manifest_episodes_returns_episode_statuses(monkeypatch) -> None:
    app.dependency_overrides[ingest_routes.get_db] = override_db
    expected_summary = ManifestSummaryRead(
        manifest_path="/repo/manifests/example-series.yaml",
        series_id="example-series",
        series_title="示例剧",
        season_label="第一季",
        language="zh-CN",
        episode_count=2,
    )
    expected_episodes = [
        EpisodeIngestStatusRead(
            episode_id="ep01",
            episode_no=1,
            title="第一集",
            filename="01.mp4",
            ingest_state="ingested",
            is_ingested=True,
            frame_count=120,
            latest_job_id=None,
            latest_job_status=JobStatus.COMPLETED,
            latest_job_stage=JobStage.PERSIST,
            latest_error_message=None,
            latest_finished_at=None,
        ),
        EpisodeIngestStatusRead(
            episode_id="ep02",
            episode_no=2,
            title="第二集",
            filename="02.mp4",
            ingest_state="queued",
            is_ingested=False,
            frame_count=0,
            latest_job_id=None,
            latest_job_status=JobStatus.QUEUED,
            latest_job_stage=JobStage.MANIFEST,
            latest_error_message=None,
            latest_finished_at=None,
        ),
    ]
    monkeypatch.setattr(
        ingest_routes.service,
        "list_manifest_episodes",
        lambda _db, _manifest_path: (expected_summary, expected_episodes),
    )

    response = client.get(
        "/ingest/manifest-episodes",
        params={"manifest_path": "/repo/manifests/example-series.yaml"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["episode_id"] == "ep01"
    assert response.json()[0]["ingest_state"] == "ingested"
    assert response.json()[1]["latest_job_status"] == "queued"


def test_list_manifest_episodes_maps_manifest_errors_to_400(monkeypatch) -> None:
    app.dependency_overrides[ingest_routes.get_db] = override_db

    def raise_manifest_error(_db: object, _manifest_path: str):
        raise ManifestError("manifest not found")

    monkeypatch.setattr(ingest_routes.service, "list_manifest_episodes", raise_manifest_error)

    response = client.get(
        "/ingest/manifest-episodes",
        params={"manifest_path": "/repo/manifests/missing.yaml"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {"detail": "manifest not found"}
