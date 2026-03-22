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
