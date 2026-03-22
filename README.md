# Drama Finder

基于 `FastAPI + PostgreSQL + pgvector + Redis/RQ` 的中文剧集截图定位系统。

当前仓库已初始化：

- 后端服务骨架
- 数据库模型与迁移骨架
- manifest 校验与元数据同步
- 入库任务编排骨架
- shot/segment 方案的过渡实现骨架
- 规格文档目录

详细方案见 [docs/general-plan.md](docs/general-plan.md) 和 [AGENTS.md](AGENTS.md)。

- 本地数据根目录固定为仓库下 `data/`，不通过环境变量配置。
- `frames.image_path` 默认保存相对 `data/` 的相对路径，例如 `series/<series_id>/<episode_id>/frames/frame_000001.jpg`。
- frame embedding 并发可通过 `.env` 中的 `FRAME_EMBEDDING_MAX_WORKERS` 调整，默认 `4`。

## 本地启动

1. 启动基础设施

```bash
docker compose -f compose.yaml up -d
```

2. 安装依赖

```bash
env UV_CACHE_DIR=.uv-cache uv sync --extra dev --extra pipeline
```

3. 执行迁移

```bash
.venv/bin/alembic upgrade head
```

4. 启动 API

```bash
make start
```

5. 启动 worker

```bash
make worker
```

- `make worker` 当前会同时消费 `ingest` 和 `embedding` 两个队列。
- 入库页 `/ingest` 会展示 `embedding_status` 与图片向量子进度；worker 终端也会输出 embedding backfill 的进度日志。

## React Web UI

当前默认 Web UI 已切到 React：

- 检索页：`http://127.0.0.1:8000/search`
- 入库页：`http://127.0.0.1:8000/ingest`
- 轻量回退页：`http://127.0.0.1:8000/demo`

### 生产式本地预览

先构建前端，再启动 FastAPI：

```bash
cd frontend
npm install
npm run build
cd ..
make start
```

构建完成后，FastAPI 会直接托管 `frontend/dist/` 里的静态资源；此时访问 `/`、`/search`、`/ingest` 就会看到 React 版页面。

如果你还没有执行 `npm run build`，那么直接访问 `8000` 下的 `/`、`/search`、`/ingest` 时只会看到一个 React shell 提示页，而不是完整前端。

### 前端开发模式

如果你要边改前端边看效果，保持 FastAPI 在 `8000` 端口运行，再单独启动 Vite：

```bash
make start
```

另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

然后访问：

- `http://127.0.0.1:5173/ui/search`
- `http://127.0.0.1:5173/ui/ingest`

`frontend/vite.config.ts` 已把 `/search`、`/ingest`、`/demo` 代理到 `http://localhost:8000`，所以检索、入库和证据图都会走本地 FastAPI。

如果你要验证真实入库任务推进，还需要额外启动 worker：

```bash
make worker
```

## ASR 标点恢复

当前默认 ASR 主链为 `Node.js + sherpa-onnx + SenseVoice Small`，可选开启 `ct-punc-c` 风格的离线标点恢复，改善中文台词黏连和断句可读性。

推荐配置：

```bash
ASR_ENABLE_PUNCTUATION=true
ASR_NODE_PUNC_MODEL_PATH=/home/james/.coli/models/sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8/model.int8.onnx
```

官方模型来源：

- 文档：`https://k2-fsa.github.io/sherpa/onnx/punctuation/pretrained_models.html`
- Release：`sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8`

开启后：

- `artifacts/asr_segments.json` 中的 `text` 会写入加标点后的文本
- 同一条 segment 会额外保留 `raw_text` 作为无标点原文，便于回溯和对比
- `shots.raw_metadata.asr_text` 与 `frames.context_asr_text` 会随重跑 ingest 一并刷新

如需回退，只需将 `ASR_ENABLE_PUNCTUATION=false`，然后重跑对应 episode ingest。
