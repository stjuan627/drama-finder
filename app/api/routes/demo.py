from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from app.api.routes.frontend import render_frontend_shell
from app.services.storage import StorageService

router = APIRouter(tags=["demo"])
ALLOWED_EVIDENCE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

LEGACY_DEMO_HTML = dedent(
    """\
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Drama Finder Legacy Demo</title>
      <style>
        :root {
          color-scheme: light;
          --bg: #f6efe4;
          --panel: rgba(255, 250, 241, 0.9);
          --line: rgba(85, 54, 32, 0.14);
          --text: #2f1f15;
          --muted: #7f6758;
          --accent: #9e4f2b;
        }

        * { box-sizing: border-box; }

        body {
          margin: 0;
          min-height: 100vh;
          font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
          color: var(--text);
          background:
            radial-gradient(circle at top left, rgba(230, 186, 127, 0.22), transparent 28%),
            linear-gradient(180deg, #fbf6ee, var(--bg));
        }

        main {
          width: min(840px, calc(100vw - 32px));
          margin: 48px auto;
          padding: 32px;
          border: 1px solid var(--line);
          border-radius: 28px;
          background: var(--panel);
          box-shadow: 0 18px 50px rgba(60, 35, 18, 0.10);
        }

        h1 {
          margin: 0 0 12px;
          font-family: "Noto Serif SC", "Songti SC", serif;
          font-size: clamp(28px, 5vw, 46px);
          line-height: 1.08;
        }

        p {
          margin: 0;
          color: var(--muted);
          line-height: 1.8;
        }

        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: 24px;
        }

        a {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 148px;
          padding: 12px 18px;
          border-radius: 999px;
          text-decoration: none;
          border: 1px solid var(--line);
          color: var(--text);
          background: rgba(255,255,255,0.72);
        }

        a.primary {
          color: white;
          background: linear-gradient(135deg, var(--accent), #ba6840);
          border-color: transparent;
        }

        .note {
          margin-top: 20px;
          padding: 14px 16px;
          border-radius: 18px;
          border: 1px dashed var(--line);
          background: rgba(255,255,255,0.58);
          font-size: 14px;
        }
      </style>
    </head>
    <body>
      <main>
        <h1>旧版内联 Demo 已退场，Web UI 现在由 React 驱动。</h1>
        <p>
          默认入口 ` / `、` /search `、` /ingest ` 已切到新的 React 页面；这里保留一个轻量回退页，方便手动跳转和检查路由。
        </p>
        <div class="actions">
          <a class="primary" href="/search">打开 React 检索页</a>
          <a href="/ingest">打开 React 入库页</a>
          <a href="/ui/search">直接访问 /ui/search</a>
          <a href="/ui/ingest">直接访问 /ui/ingest</a>
        </div>
        <div class="note">
          ` /demo/evidence ` 仍继续提供证据图代理；如果你在本地开发 React，请先启动 FastAPI API，再启动 `frontend/` 下的 Vite 开发服务器。
        </div>
      </main>
    </body>
    </html>
    """
)


def resolve_evidence_path(raw_path: str) -> Path:
    storage_service = StorageService()
    data_root = storage_service.data_root()
    resolved = storage_service.resolve_data_path(raw_path)
    try:
        resolved.relative_to(data_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="evidence image not found") from exc
    if resolved.suffix.lower() not in ALLOWED_EVIDENCE_SUFFIXES:
        raise HTTPException(status_code=404, detail="evidence image not found")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="evidence image not found")
    return resolved


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo_home() -> str:
    return render_frontend_shell("search")


@router.get("/search", response_class=HTMLResponse, include_in_schema=False)
def search_page() -> str:
    return render_frontend_shell("search")


@router.get("/ingest", response_class=HTMLResponse, include_in_schema=False)
def ingest_page() -> str:
    return render_frontend_shell("ingest")


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo_page() -> str:
    return LEGACY_DEMO_HTML


@router.get("/demo/evidence", include_in_schema=False)
def demo_evidence(path: str = Query(min_length=1)) -> FileResponse:
    return FileResponse(resolve_evidence_path(path))
