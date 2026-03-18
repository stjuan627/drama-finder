from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["demo"])


DEMO_HTML = """<!doctype html>
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

    .page {
      width: min(1180px, calc(100vw - 32px));
      margin: 28px auto 48px;
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
      max-width: 680px;
      color: var(--muted);
      line-height: 1.8;
      font-size: 15px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .grid {
      display: grid;
      grid-template-columns: 1.08fr 0.92fr;
      gap: 18px;
      margin-top: 18px;
    }

    .stack {
      display: grid;
      gap: 18px;
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

    .field-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
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
      min-height: 110px;
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

    .results {
      display: grid;
      gap: 12px;
    }

    .hit {
      border: 1px solid rgba(85, 54, 32, 0.12);
      border-radius: 18px;
      background: var(--panel-strong);
      padding: 16px;
    }

    .hit-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 10px;
    }

    .hit-title {
      font-size: 16px;
      font-weight: 700;
    }

    .score {
      color: var(--accent);
      font-size: 13px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .kv {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .evidence {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed rgba(85, 54, 32, 0.15);
      color: var(--text);
    }

    .muted {
      color: var(--muted);
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
    }

    .ok { color: var(--success); }
    .bad { color: var(--danger); }

    @media (max-width: 980px) {
      .grid { grid-template-columns: 1fr; }
      .field-grid { grid-template-columns: 1fr; }
      .actions { flex-direction: column; }
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="eyebrow">Drama Finder / Demo</div>
      <h1>用一张图，或者一句台词，直接追到剧集区间。</h1>
      <p>
        这是当前后端闭环的最小演示页：提交单集入库任务、轮询任务状态、上传截图做图片检索、输入台词做文本检索，
        最终返回 `剧集 + 时间区间` 候选。
      </p>
    </section>

    <section class="grid">
      <div class="stack">
        <section class="panel">
          <h2>入库任务</h2>
          <div class="sub">
            先提交 `manifest + series_id + episode_id`，
            再用右侧状态卡轮询任务进度。
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

        <section class="panel">
          <h2>截图检索</h2>
          <div class="sub">上传截图后，直接走 `/search/image`，返回最可能的时间区间候选。</div>
          <div class="field-grid">
            <div class="wide">
              <label for="imageFile">截图文件</label>
              <input id="imageFile" type="file" accept="image/*" />
            </div>
          </div>
          <div class="actions">
            <button class="primary" id="runImageSearch">开始图片检索</button>
          </div>
        </section>

        <section class="panel">
          <h2>台词检索</h2>
          <div class="sub">
            输入一句台词后，直接走 `/search/text`，
            当前已经带有轻量模糊匹配增强。
          </div>
          <label for="queryText">台词文本</label>
          <textarea id="queryText">皇上驾到</textarea>
          <div class="actions">
            <button class="primary" id="runTextSearch">开始文本检索</button>
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

        <section class="panel">
          <h2>检索结果</h2>
          <div id="searchMeta" class="muted">尚未执行检索。</div>
          <div id="searchResults" class="results"></div>
        </section>
      </div>
    </section>
  </main>

  <script>
    const state = { jobId: "" };

    const el = {
      manifestPath: document.getElementById("manifestPath"),
      seriesId: document.getElementById("seriesId"),
      episodeId: document.getElementById("episodeId"),
      imageFile: document.getElementById("imageFile"),
      queryText: document.getElementById("queryText"),
      submitIngest: document.getElementById("submitIngest"),
      pollJob: document.getElementById("pollJob"),
      runImageSearch: document.getElementById("runImageSearch"),
      runTextSearch: document.getElementById("runTextSearch"),
      jobId: document.getElementById("jobId"),
      jobStatus: document.getElementById("jobStatus"),
      jobStage: document.getElementById("jobStage"),
      jobProgress: document.getElementById("jobProgress"),
      jobMessage: document.getElementById("jobMessage"),
      jobPayload: document.getElementById("jobPayload"),
      searchMeta: document.getElementById("searchMeta"),
      searchResults: document.getElementById("searchResults"),
    };

    function secondsToLabel(value) {
      const total = Math.max(0, Math.floor(value));
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
        state.jobId = payload.id;
        renderJob(payload);
      } catch (error) {
        el.jobMessage.innerHTML = `<span class="bad">${error.message}</span>`;
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
        el.jobMessage.innerHTML = `<span class="bad">${error.message}</span>`;
      } finally {
        setBusy(el.pollJob, false);
      }
    }

    function renderJob(payload) {
      state.jobId = payload.id;
      el.jobId.textContent = payload.id;
      el.jobStatus.textContent = payload.status || "-";
      el.jobStage.textContent = payload.current_stage || "-";
      el.jobProgress.textContent =
        `${payload.progress_current ?? 0} / ${payload.progress_total ?? 0}`;
      const messageClass =
        payload.status === "completed" ? "ok" : payload.status === "failed" ? "bad" : "";
      const detail = payload.error_message ? `错误：${payload.error_message}` : "任务记录已更新。";
      el.jobMessage.innerHTML = `<span class="${messageClass}">${detail}</span>`;
      el.jobPayload.textContent = JSON.stringify(payload, null, 2);
    }

    function renderSearchResult(payload, kind) {
      el.searchMeta.innerHTML =
        `${kind}检索完成 · low_confidence = <strong>${payload.low_confidence}</strong> ` +
        `· hits = <strong>${payload.hits.length}</strong>`;
      el.searchResults.innerHTML = payload.hits.map((hit, index) => `
        <article class="hit">
          <div class="hit-head">
            <div class="hit-title">候选 ${index + 1} · ${hit.series_id} / ${hit.episode_id}</div>
            <div class="score">score ${Number(hit.score).toFixed(4)}</div>
          </div>
          <div class="kv">
            <div>
              区间：${secondsToLabel(hit.matched_start_ts)} -
              ${secondsToLabel(hit.matched_end_ts)}
            </div>
            <div>秒值：${hit.matched_start_ts.toFixed(2)} - ${hit.matched_end_ts.toFixed(2)}</div>
          </div>
          <div class="evidence">
            <div>
              <strong>图片证据</strong>：
              ${hit.evidence_images.length ? hit.evidence_images.join(", ") : "无"}
            </div>
            <div>
              <strong>文本证据</strong>：
              ${hit.evidence_text.length ? hit.evidence_text.join(" | ") : "无"}
            </div>
          </div>
        </article>
      `).join("") || '<div class="muted">没有命中候选。</div>';
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
        el.searchMeta.innerHTML = `<span class="bad">${error.message}</span>`;
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
        el.searchMeta.innerHTML = `<span class="bad">${error.message}</span>`;
        el.searchResults.innerHTML = "";
      } finally {
        setBusy(el.runTextSearch, false);
      }
    }

    el.submitIngest.addEventListener("click", submitIngest);
    el.pollJob.addEventListener("click", pollJob);
    el.runImageSearch.addEventListener("click", runImageSearch);
    el.runTextSearch.addEventListener("click", runTextSearch);
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo_home() -> str:
    return DEMO_HTML


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo_page() -> str:
    return DEMO_HTML
