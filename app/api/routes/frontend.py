from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["frontend"])

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_DIR / "index.html"


def _inject_page_marker(html: str, page: str) -> str:
    marker = (
        f'<meta name="drama-finder-route" content="{page}">'
        f'<script>window.__DRAMA_FINDER_PAGE__ = "{page}";</script>'
    )
    if "</head>" in html:
        return html.replace("</head>", f"{marker}</head>", 1)
    return f"{marker}{html}"


def render_frontend_shell(page: str) -> str:
    if FRONTEND_INDEX_PATH.is_file():
        return _inject_page_marker(FRONTEND_INDEX_PATH.read_text(encoding="utf-8"), page)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="drama-finder-route" content="{page}">
  <title>Drama Finder React Shell</title>
  <script>window.__DRAMA_FINDER_PAGE__ = \"{page}\";</script>
</head>
<body data-react-shell="true">
  <div id="root"></div>
  <div style="max-width: 960px; margin: 48px auto; padding: 0 16px; font-family: sans-serif; color: #2f1f15;">
    <h1>Drama Finder React Shell</h1>
    <p>当前 React 构建产物尚未生成。请在 `frontend/` 下执行 `npm run build` 后刷新页面。</p>
    <p>当前页面：<strong>{page}</strong></p>
  </div>
</body>
</html>"""


@router.get("/ui/search", response_class=HTMLResponse, include_in_schema=False)
def ui_search_page() -> str:
    return render_frontend_shell("search")


@router.get("/ui/ingest", response_class=HTMLResponse, include_in_schema=False)
def ui_ingest_page() -> str:
    return render_frontend_shell("ingest")
