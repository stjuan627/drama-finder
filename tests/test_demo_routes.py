from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes import demo as demo_routes
from app.main import app


client = TestClient(app)


def test_root_serves_search_page() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'name="drama-finder-route" content="search"' in response.text
    assert 'window.__DRAMA_FINDER_PAGE__ = "search"' in response.text


def test_search_alias_serves_search_page() -> None:
    response = client.get("/search")

    assert response.status_code == 200
    assert 'name="drama-finder-route" content="search"' in response.text


def test_ingest_page_is_separate() -> None:
    response = client.get("/ingest")

    assert response.status_code == 200
    assert 'name="drama-finder-route" content="ingest"' in response.text
    assert 'window.__DRAMA_FINDER_PAGE__ = "ingest"' in response.text


def test_ui_search_shell_is_available() -> None:
    response = client.get("/ui/search")

    assert response.status_code == 200
    assert 'name="drama-finder-route" content="search"' in response.text


def test_ui_ingest_shell_is_available() -> None:
    response = client.get("/ui/ingest")

    assert response.status_code == 200
    assert 'name="drama-finder-route" content="ingest"' in response.text


def test_demo_alias_keeps_working() -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    assert "旧版内联 Demo 已退场" in response.text
    assert "React 驱动" in response.text
    assert "/ui/search" in response.text


def test_demo_evidence_rejects_outside_data_root() -> None:
    response = client.get("/demo/evidence", params={"path": "/etc/passwd"})

    assert response.status_code == 404


def test_demo_evidence_serves_image_within_data_root(tmp_path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    image_path = data_root / "series" / "sample" / "frames" / "shot-001.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake-image-bytes")
    monkeypatch.setattr(
        demo_routes.StorageService,
        "data_root",
        staticmethod(lambda: data_root.resolve()),
    )

    response = client.get(
        "/demo/evidence",
        params={"path": str(Path("series") / "sample" / "frames" / "shot-001.jpg")},
    )

    assert response.status_code == 200
    assert response.content == b"fake-image-bytes"


def test_demo_evidence_rejects_non_image_within_data_root(tmp_path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    artifact_path = data_root / "series" / "sample" / "artifacts" / "asr_segments.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        demo_routes.StorageService,
        "data_root",
        staticmethod(lambda: data_root.resolve()),
    )

    response = client.get(
        "/demo/evidence",
        params={"path": str(Path("series") / "sample" / "artifacts" / "asr_segments.json")},
    )

    assert response.status_code == 404
