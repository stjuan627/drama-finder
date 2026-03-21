from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import get_settings

router = APIRouter(tags=["demo"])
settings = get_settings()
ALLOWED_EVIDENCE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


COMMON_HEAD = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Drama Finder Demo</title>
  <style>
    :root {
      --bg: #f3ecdf;
      --panel: rgba(255, 250, 241, 0.84);
      --panel-strong: #fff9ef;
      --line: rgba(85, 54, 32, 0.18);
      --text: #2f1f15;
      --muted: #7f6758;
      --accent: #9e4f2b;
      --accent-soft: #e8b487;
      --success: #2f7d57;
      --danger: #b0493a;
      --shadow: 0 18px 50px rgba(60, 35, 18, 0.10);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(230, 186, 127, 0.28), transparent 28%),
        radial-gradient(circle at bottom right, rgba(136, 73, 36, 0.12), transparent 26%),
        linear-gradient(180deg, #fbf6ee, var(--bg));
      font-family: "Noto Serif SC", "Songti SC", "STSong", serif;
    }

    a { color: inherit; }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 10;
      backdrop-filter: blur(16px);
      background: rgba(251, 246, 238, 0.78);
      border-bottom: 1px solid rgba(85, 54, 32, 0.08);
    }

    .topbar-inner {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 14px 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .brand {
      display: grid;
      gap: 2px;
    }

    .brand-mark {
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--accent);
    }

    .brand-title {
      font-size: 18px;
      font-weight: 700;
    }

    .nav {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .nav-link {
      padding: 10px 16px;
      border-radius: 999px;
      border: 1px solid rgba(85, 54, 32, 0.12);
      background: rgba(255,255,255,0.7);
      text-decoration: none;
      color: var(--muted);
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      font-size: 14px;
      transition: transform .18s ease, border-color .18s ease, color .18s ease, background .18s ease;
    }

    .nav-link:hover {
      transform: translateY(-1px);
      color: var(--text);
    }

    .nav-link.active {
      color: white;
      background: linear-gradient(135deg, var(--accent), #ba6840);
      border-color: transparent;
      box-shadow: 0 12px 24px rgba(158, 79, 43, 0.18);
    }

    .page {
      width: min(1180px, calc(100vw - 32px));
      margin: 28px auto 48px;
      display: grid;
      gap: 18px;
    }

    .hero {
      position: relative;
      overflow: hidden;
      padding: 28px 30px 30px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(255,255,255,0.86), rgba(255,245,230,0.76));
      box-shadow: var(--shadow);
    }

    .hero:before,
    .hero:after {
      content: "";
      position: absolute;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(158,79,43,0.14), transparent 68%);
      pointer-events: none;
    }

    .hero:before {
      width: 260px;
      height: 260px;
      top: -110px;
      right: -70px;
    }

    .hero:after {
      width: 220px;
      height: 220px;
      bottom: -110px;
      left: -80px;
    }

    .eyebrow {
      margin: 0 0 12px;
      color: var(--accent);
      letter-spacing: 0.16em;
      text-transform: uppercase;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      font-size: 12px;
    }

    h1 {
      margin: 0;
      max-width: 760px;
      line-height: 1.06;
      font-size: clamp(34px, 6vw, 64px);
      font-weight: 700;
    }

    .hero p {
      margin: 18px 0 0;
      max-width: 720px;
      color: var(--muted);
      line-height: 1.8;
      font-size: 15px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .hero-cta {
      margin-top: 20px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 22px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }

    .panel h2 {
      margin: 0 0 16px;
      font-size: 20px;
    }

    .sub {
      margin: -8px 0 18px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .search-shell {
      display: grid;
      gap: 18px;
    }

    .search-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.95fr);
      gap: 18px;
      align-items: start;
    }

    .ingest-grid {
      display: grid;
      grid-template-columns: 1.08fr 0.92fr;
      gap: 18px;
    }

    .stack {
      display: grid;
      gap: 18px;
    }

    .search-form {
      display: grid;
      gap: 16px;
    }

    .field-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .search-actions {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 220px;
      gap: 12px;
      align-items: end;
    }

    .search-hint-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }

    .hint-card {
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.62);
      border: 1px solid rgba(85, 54, 32, 0.08);
    }

    .hint-card strong {
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
    }

    .hint-card span {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    label {
      display: block;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 12px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    input,
    textarea,
    button {
      width: 100%;
      font: inherit;
    }

    input,
    textarea {
      border: 1px solid rgba(85, 54, 32, 0.16);
      border-radius: 16px;
      background: rgba(255,255,255,0.86);
      color: var(--text);
      padding: 14px 15px;
      outline: none;
      transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    input:focus,
    textarea:focus {
      border-color: rgba(158, 79, 43, 0.55);
      box-shadow: 0 0 0 4px rgba(158, 79, 43, 0.08);
      transform: translateY(-1px);
    }

    textarea {
      min-height: 124px;
      resize: vertical;
    }

    .wide {
      grid-column: 1 / -1;
    }

    .actions {
      display: flex;
      gap: 10px;
      margin-top: 14px;
    }

    button {
      border: 0;
      cursor: pointer;
      border-radius: 999px;
      padding: 13px 18px;
      font-weight: 700;
      transition: transform .18s ease, opacity .18s ease, box-shadow .18s ease;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    button:hover { transform: translateY(-1px); }
    button:disabled { cursor: wait; opacity: 0.7; transform: none; }

    .primary {
      color: white;
      background: linear-gradient(135deg, var(--accent), #ba6840);
      box-shadow: 0 12px 24px rgba(158, 79, 43, 0.22);
    }

    .secondary {
      color: var(--text);
      background: rgba(255,255,255,0.92);
      border: 1px solid rgba(85, 54, 32, 0.14);
    }

    .status-card {
      display: grid;
      gap: 12px;
    }

    .status-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .pill {
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.92);
      border: 1px solid rgba(85, 54, 32, 0.12);
      font-size: 12px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .log,
    .json-box {
      border-radius: 18px;
      background: rgba(46, 29, 18, 0.92);
      color: #f5eee3;
      padding: 14px 16px;
      font-size: 12px;
      line-height: 1.7;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
    }

    .results-panel {
      display: grid;
      gap: 16px;
    }

    .results {
      display: grid;
      gap: 14px;
      min-height: 52px;
    }

    .results-empty {
      padding: 16px 18px;
      border-radius: 18px;
      background: rgba(255,255,255,0.7);
      border: 1px dashed rgba(85, 54, 32, 0.16);
      color: var(--muted);
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      line-height: 1.8;
    }

    .hit {
      display: grid;
      grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
      gap: 18px;
      border: 1px solid rgba(85, 54, 32, 0.12);
      border-radius: 22px;
      background: var(--panel-strong);
      padding: 18px;
    }

    .hit-visual {
      display: grid;
      gap: 10px;
      align-content: start;
    }

    .hit-main-image {
      position: relative;
      overflow: hidden;
      border-radius: 18px;
      background: linear-gradient(135deg, rgba(232, 180, 135, 0.18), rgba(255,255,255,0.8));
      border: 1px solid rgba(85, 54, 32, 0.08);
      min-height: 168px;
    }

    .hit-main-image img {
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: cover;
      background: rgba(255,255,255,0.75);
    }

    .image-fallback {
      display: grid;
      gap: 8px;
      align-content: center;
      min-height: 168px;
      padding: 18px;
      color: var(--muted);
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      line-height: 1.7;
    }

    .thumb-strip {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 2px;
    }

    .thumb {
      position: relative;
      flex: 0 0 76px;
      overflow: hidden;
      border-radius: 12px;
      border: 1px solid rgba(85, 54, 32, 0.10);
      background: rgba(255,255,255,0.82);
    }

    .thumb img {
      display: block;
      width: 100%;
      aspect-ratio: 16 / 10;
      object-fit: cover;
      background: rgba(255,255,255,0.78);
    }

    .thumb-fallback {
      display: grid;
      place-items: center;
      aspect-ratio: 16 / 10;
      color: var(--muted);
      font-size: 11px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .evidence-paths {
      display: grid;
      gap: 6px;
      font-size: 12px;
      color: var(--muted);
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      line-height: 1.6;
    }

    .path-chip {
      display: inline-flex;
      max-width: 100%;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(85, 54, 32, 0.12);
      background: rgba(255,255,255,0.78);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .hit-copy {
      display: grid;
      gap: 12px;
      align-content: start;
    }

    .hit-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }

    .hit-title {
      font-size: 18px;
      font-weight: 700;
    }

    .score {
      color: var(--accent);
      font-size: 13px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      white-space: nowrap;
    }

    .time-band {
      display: inline-flex;
      align-items: center;
      width: fit-content;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(232, 180, 135, 0.22);
      color: var(--accent);
      font-size: 13px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      font-weight: 700;
    }

    .kv {
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .evidence-block {
      display: grid;
      gap: 8px;
      padding-top: 12px;
      border-top: 1px dashed rgba(85, 54, 32, 0.15);
    }

    .evidence-label {
      color: var(--text);
      font-size: 13px;
      font-weight: 700;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .evidence-text {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.8;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .muted {
      color: var(--muted);
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .ok { color: var(--success); }
    .bad { color: var(--danger); }

    @media (max-width: 980px) {
      .search-grid,
      .ingest-grid,
      .field-grid,
      .search-actions,
      .search-hint-grid,
      .hit {
        grid-template-columns: 1fr;
      }

      .actions {
        flex-direction: column;
      }

      .topbar-inner {
        align-items: start;
        flex-direction: column;
      }

      .hit-head {
        align-items: start;
        flex-direction: column;
      }
    }
  </style>
</head>
<body>
"""

COMMON_FOOTER = """
</body>
</html>
"""

SEARCH_BODY = """
  <main class="page">
    <section class="hero">
      <div class="eyebrow">Drama Finder / Search</div>
      <h1>默认进入检索，把线索压缩成一张图或一句台词。</h1>
      <p>
        当前 demo 已拆成检索页与入库页。这里优先承载日常查询：顶部输入线索，下面直接查看候选区间、置信度、文本证据，
        以及可附带的关联截图。
      </p>
      <div class="hero-cta">
        <a class="nav-link active" href="/search">进入检索</a>
        <a class="nav-link" href="/ingest">切换到入库</a>
      </div>
    </section>

    <section class="search-shell">
      <section class="panel search-grid">
        <div class="search-form">
          <div>
            <h2>常规搜索框</h2>
            <div class="sub">
              文本检索作为主入口，截图检索作为补充入口；两种方式都会把结果落到下方统一列表。
            </div>
          </div>
          <div>
            <label for="queryText">台词文本</label>
            <textarea id="queryText" placeholder="例如：皇上驾到">皇上驾到</textarea>
          </div>
          <div class="search-actions">
            <div>
              <label for="imageFile">关联截图（可选）</label>
              <input id="imageFile" type="file" accept="image/*" />
            </div>
            <button class="primary" id="runTextSearch">开始文本检索</button>
          </div>
          <div class="actions">
            <button class="secondary" id="runImageSearch">仅用截图检索</button>
          </div>
        </div>

        <div class="search-hint-grid">
          <div class="hint-card">
            <strong>默认检索页</strong>
            <span>打开 demo 就落到查询流程，避免被入库表单分散注意力。</span>
          </div>
          <div class="hint-card">
            <strong>结果附图</strong>
            <span>命中结果可展示关联截图；若图片暂不可直连，也会保留路径证据。</span>
          </div>
          <div class="hint-card">
            <strong>区间优先</strong>
            <span>仍以 `剧集 + 时间区间` 为主结果，截图与文本只作为证据补充。</span>
          </div>
        </div>
      </section>

      <section class="panel results-panel">
        <div>
          <h2>结果列表</h2>
          <div id="searchMeta" class="muted">尚未执行检索。</div>
        </div>
        <div id="searchResults" class="results"></div>
      </section>
    </section>
  </main>
"""

INGEST_BODY = """
  <main class="page">
    <section class="hero">
      <div class="eyebrow">Drama Finder / Ingest</div>
      <h1>把入库流程收进独立页面，让检索入口保持轻量。</h1>
      <p>
        这里保留提交单集任务与轮询任务状态的完整闭环。切换页面不会改变后端契约，仍然沿用现有入库 API 和任务状态结构。
      </p>
      <div class="hero-cta">
        <a class="nav-link" href="/search">回到检索</a>
        <a class="nav-link active" href="/ingest">当前是入库页</a>
      </div>
    </section>

    <section class="ingest-grid">
      <div class="stack">
        <section class="panel">
          <h2>入库任务</h2>
          <div class="sub">
            先提交 `manifest + series_id + episode_id`，再用右侧状态卡轮询任务进度。
          </div>
          <div class="field-grid">
            <div class="wide">
              <label for="manifestPath">Manifest 路径</label>
              <input id="manifestPath" value="/tmp/wufulinmen-test-manifest.yaml" />
            </div>
            <div>
              <label for="seriesId">Series ID</label>
              <input id="seriesId" value="wufulinmen" />
            </div>
            <div>
              <label for="episodeId">Episode ID</label>
              <input id="episodeId" value="ep02" />
            </div>
          </div>
          <div class="actions">
            <button class="primary" id="submitIngest">提交入库</button>
            <button class="secondary" id="pollJob">刷新状态</button>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="panel status-card">
          <h2>任务状态</h2>
          <div class="status-strip">
            <div class="pill">Job ID：<span id="jobId" class="muted">未提交</span></div>
            <div class="pill">状态：<span id="jobStatus" class="muted">-</span></div>
            <div class="pill">阶段：<span id="jobStage" class="muted">-</span></div>
            <div class="pill">进度：<span id="jobProgress" class="muted">-</span></div>
          </div>
          <div id="jobMessage" class="muted">提交任务后，这里会显示实时状态。</div>
          <div class="json-box" id="jobPayload">{}</div>
        </section>
      </div>
    </section>
  </main>
"""

SEARCH_SCRIPT = """
  <script>
    const el = {
      imageFile: document.getElementById("imageFile"),
      queryText: document.getElementById("queryText"),
      runImageSearch: document.getElementById("runImageSearch"),
      runTextSearch: document.getElementById("runTextSearch"),
      searchMeta: document.getElementById("searchMeta"),
      searchResults: document.getElementById("searchResults"),
    };

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function secondsToLabel(value) {
      const total = Math.max(0, Math.floor(Number(value) || 0));
      const hh = String(Math.floor(total / 3600)).padStart(2, "0");
      const mm = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
      const ss = String(total % 60).padStart(2, "0");
      return `${hh}:${mm}:${ss}`;
    }

    function setBusy(button, busy, text) {
      button.disabled = busy;
      if (text) {
        button.dataset.originalText ??= button.textContent;
        button.textContent = busy ? text : button.dataset.originalText;
      }
    }

    function resolveEvidenceUrl(path) {
      return `/demo/evidence?path=${encodeURIComponent(path)}`;
    }

    function renderImageBlock(path, className, fallbackClass, alt) {
      const safePath = escapeHtml(path);
      const src = escapeHtml(resolveEvidenceUrl(path));
      return `
        <img class="${className}" src="${src}" alt="${alt}"
          onerror="this.style.display='none'; this.nextElementSibling.hidden=false;">
        <div class="${fallbackClass}" hidden>图片暂不可见</div>
        <div class="evidence-paths"><span class="path-chip" title="${safePath}">${safePath}</span></div>
      `;
    }

    function renderSearchResult(payload, kind) {
      el.searchMeta.innerHTML =
        `${kind}检索完成 · low_confidence = <strong>${payload.low_confidence}</strong> ` +
        `· hits = <strong>${payload.hits.length}</strong>`;

      if (!payload.hits.length) {
        el.searchResults.innerHTML =
          '<div class="results-empty">没有命中候选。若这是新剧集，可先去入库页补录对应剧集后再回来检索。</div>';
        return;
      }

      el.searchResults.innerHTML = payload.hits.map((hit, index) => {
        const images = Array.isArray(hit.evidence_images) ? hit.evidence_images.filter(Boolean) : [];
        const texts = Array.isArray(hit.evidence_text) ? hit.evidence_text.filter(Boolean) : [];
        const safeSeries = escapeHtml(hit.series_id);
        const safeEpisode = escapeHtml(hit.episode_id);
        const mainVisual = images.length
          ? `<div class="hit-main-image">${renderImageBlock(images[0], "evidence-main", "image-fallback", "关联截图")}</div>`
          : '<div class="hit-main-image"><div class="image-fallback">暂无关联截图<br>本次结果仍可根据区间与文本证据判断。</div></div>';
        const thumbs = images.length > 1
          ? `<div class="thumb-strip">${images.slice(1, 4).map((path) => {
              const safePath = escapeHtml(path);
              const src = escapeHtml(resolveEvidenceUrl(path));
              return `
                <div class="thumb" title="${safePath}">
                  <img src="${src}" alt="关联截图缩略图"
                    onerror="this.style.display='none'; this.nextElementSibling.hidden=false;">
                  <div class="thumb-fallback" hidden>不可预览</div>
                </div>
              `;
            }).join("")}</div>`
          : "";

        return `
          <article class="hit">
            <div class="hit-visual">
              ${mainVisual}
              ${thumbs}
            </div>
            <div class="hit-copy">
              <div class="hit-head">
                <div class="hit-title">候选 ${index + 1} · ${safeSeries} / ${safeEpisode}</div>
                <div class="score">score ${Number(hit.score).toFixed(4)}</div>
              </div>
              <div class="time-band">
                ${secondsToLabel(hit.matched_start_ts)} - ${secondsToLabel(hit.matched_end_ts)}
              </div>
              <div class="kv">
                <div>秒值：${Number(hit.matched_start_ts).toFixed(2)} - ${Number(hit.matched_end_ts).toFixed(2)}</div>
                <div>关联截图：${images.length ? `${images.length} 张` : "无"}</div>
              </div>
              <div class="evidence-block">
                <div class="evidence-label">文本证据</div>
                <div class="evidence-text">${texts.length ? texts.map(escapeHtml).join(" | ") : "无"}</div>
              </div>
            </div>
          </article>
        `;
      }).join("");
    }

    async function runImageSearch() {
      const file = el.imageFile.files?.[0];
      if (!file) {
        el.searchMeta.innerHTML = '<span class="bad">请先选择截图文件。</span>';
        return;
      }
      setBusy(el.runImageSearch, true, "检索中...");
      try {
        const form = new FormData();
        form.append("file", file);
        const response = await fetch("/search/image", { method: "POST", body: form });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || JSON.stringify(payload));
        renderSearchResult(payload, "图片");
      } catch (error) {
        el.searchMeta.innerHTML = `<span class="bad">${escapeHtml(error.message)}</span>`;
        el.searchResults.innerHTML = "";
      } finally {
        setBusy(el.runImageSearch, false);
      }
    }

    async function runTextSearch() {
      const query = el.queryText.value.trim();
      if (!query) {
        el.searchMeta.innerHTML = '<span class="bad">请输入台词文本。</span>';
        return;
      }
      setBusy(el.runTextSearch, true, "检索中...");
      try {
        const response = await fetch("/search/text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, limit: 5 }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || JSON.stringify(payload));
        renderSearchResult(payload, "文本");
      } catch (error) {
        el.searchMeta.innerHTML = `<span class="bad">${escapeHtml(error.message)}</span>`;
        el.searchResults.innerHTML = "";
      } finally {
        setBusy(el.runTextSearch, false);
      }
    }

    el.runImageSearch.addEventListener("click", runImageSearch);
    el.runTextSearch.addEventListener("click", runTextSearch);
  </script>
"""

INGEST_SCRIPT = """
  <script>
    const state = { jobId: window.localStorage.getItem("demo.jobId") || "" };

    const el = {
      manifestPath: document.getElementById("manifestPath"),
      seriesId: document.getElementById("seriesId"),
      episodeId: document.getElementById("episodeId"),
      submitIngest: document.getElementById("submitIngest"),
      pollJob: document.getElementById("pollJob"),
      jobId: document.getElementById("jobId"),
      jobStatus: document.getElementById("jobStatus"),
      jobStage: document.getElementById("jobStage"),
      jobProgress: document.getElementById("jobProgress"),
      jobMessage: document.getElementById("jobMessage"),
      jobPayload: document.getElementById("jobPayload"),
    };

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function setBusy(button, busy, text) {
      button.disabled = busy;
      if (text) {
        button.dataset.originalText ??= button.textContent;
        button.textContent = busy ? text : button.dataset.originalText;
      }
    }

    function renderJob(payload) {
      state.jobId = payload.id;
      window.localStorage.setItem("demo.jobId", payload.id);
      el.jobId.textContent = payload.id;
      el.jobStatus.textContent = payload.status || "-";
      el.jobStage.textContent = payload.current_stage || "-";
      el.jobProgress.textContent = `${payload.progress_current ?? 0} / ${payload.progress_total ?? 0}`;
      const messageClass =
        payload.status === "completed" ? "ok" : payload.status === "failed" ? "bad" : "";
      const detail = payload.error_message ? `错误：${payload.error_message}` : "任务记录已更新。";
      el.jobMessage.innerHTML = `<span class="${messageClass}">${escapeHtml(detail)}</span>`;
      el.jobPayload.textContent = JSON.stringify(payload, null, 2);
    }

    async function submitIngest() {
      setBusy(el.submitIngest, true, "提交中...");
      try {
        const response = await fetch("/ingest/episode", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            manifest_path: el.manifestPath.value.trim(),
            series_id: el.seriesId.value.trim(),
            episode_id: el.episodeId.value.trim(),
          }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || JSON.stringify(payload));
        renderJob(payload);
      } catch (error) {
        el.jobMessage.innerHTML = `<span class="bad">${escapeHtml(error.message)}</span>`;
      } finally {
        setBusy(el.submitIngest, false);
      }
    }

    async function pollJob() {
      if (!state.jobId) {
        el.jobMessage.innerHTML = '<span class="bad">请先提交一个任务。</span>';
        return;
      }
      setBusy(el.pollJob, true, "刷新中...");
      try {
        const response = await fetch(`/ingest/${state.jobId}`);
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || JSON.stringify(payload));
        renderJob(payload);
      } catch (error) {
        el.jobMessage.innerHTML = `<span class="bad">${escapeHtml(error.message)}</span>`;
      } finally {
        setBusy(el.pollJob, false);
      }
    }

    if (state.jobId) {
      el.jobId.textContent = state.jobId;
      el.jobMessage.textContent = "检测到上一次任务 ID，可直接刷新状态继续查看。";
    }

    el.submitIngest.addEventListener("click", submitIngest);
    el.pollJob.addEventListener("click", pollJob);
  </script>
"""


def nav_html(active: str) -> str:
    search_class = "nav-link active" if active == "search" else "nav-link"
    ingest_class = "nav-link active" if active == "ingest" else "nav-link"
    return (
        '<header class="topbar">'
        '<div class="topbar-inner">'
        '<div class="brand">'
        '<div class="brand-mark">Drama Finder</div>'
        '<div class="brand-title">剧集片段定位 Demo</div>'
        "</div>"
        '<nav class="nav">'
        f'<a class="{search_class}" href="/search">检索</a>'
        f'<a class="{ingest_class}" href="/ingest">入库</a>'
        "</nav>"
        "</div>"
        "</header>"
    )


def build_page(body: str, script: str, active: str) -> str:
    return "".join([COMMON_HEAD, nav_html(active), body, script, COMMON_FOOTER])


SEARCH_HTML = build_page(SEARCH_BODY, SEARCH_SCRIPT, "search")
INGEST_HTML = build_page(INGEST_BODY, INGEST_SCRIPT, "ingest")


def resolve_evidence_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    data_root = settings.data_path.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (data_root / candidate).resolve()
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
    return SEARCH_HTML


@router.get("/search", response_class=HTMLResponse, include_in_schema=False)
def search_page() -> str:
    return SEARCH_HTML


@router.get("/ingest", response_class=HTMLResponse, include_in_schema=False)
def ingest_page() -> str:
    return INGEST_HTML


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo_page() -> str:
    return SEARCH_HTML


@router.get("/demo/evidence", include_in_schema=False)
def demo_evidence(path: str = Query(min_length=1)) -> FileResponse:
    return FileResponse(resolve_evidence_path(path))
