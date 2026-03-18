# 默认值规范

## 运行默认值
- `FRAME_INDEX_INTERVAL_SECONDS = 3`
- `IMAGE_SEARCH_TOP_K = 10`
- `TEXT_SEARCH_TOP_K = 20`
- `SHOT_KEYFRAMES_PER_SHOT = 2`
- `INTRO_DURATION_SECONDS = 0`
- `OUTRO_DURATION_SECONDS = 0`
- `JOB_TIMEOUT_SECONDS = 7200`
- `JOB_RETRY_COUNT = 1`
- `LOW_CONFIDENCE_THRESHOLD = 0.35`
- `INGEST_SKIP_EMBEDDINGS = false`（保留兼容；首轮 ingest 固定采用 deferred）

## 模型默认值
- `gemini_embedding_model = gemini-embedding-2-preview`
- `embedding_dimensions = 3072`
- `asr_backend = node`
- `asr_model_name = iic/SenseVoiceSmall`
- `asr_model_dir = ""`（为空表示首次按模型名自动下载）
- `asr_vad_model_name = funasr/fsmn-vad-onnx`
- `asr_vad_model_dir = ""`
- `asr_device = cpu`
- `asr_cpu_cores = 2`
- `asr_compute_type = int8`
- `asr_stream_chunk_seconds = 30`
- `asr_vad_merge_gap_ms = 300`
- `asr_segment_max_seconds = 30`
- `asr_node_project_dir = ~/works/tooling/coli`
- `asr_node_cli_path = scripts/node_stream_asr.mjs`
- `asr_node_model_dir = ""`
- `asr_node_vad_model_path = ""`

## 环境变量默认值
- `APP_HOST = 0.0.0.0`
- `APP_PORT = 8000`
- `DATABASE_URL = postgresql+psycopg://postgres:postgres@localhost:5432/drama_finder`
- `REDIS_URL = redis://localhost:6379/0`
- `DATA_ROOT = ./data`
- `MANIFEST_ROOT = ./manifests`

## 默认值使用规则
- 所有实现文档中的数值默认项统一引用本文件。
- 业务代码中的常量应与本文件保持一致。
- 变更任何默认值时，必须同步修改本文件和对应代码常量。
- `FRAME_INDEX_INTERVAL_SECONDS = 3` 表示图片路径默认每 3 秒抽一帧。
- `INTRO_DURATION_SECONDS` 与 `OUTRO_DURATION_SECONDS` 仅影响索引排除范围，不影响时间轴本身。
- `SHOT_KEYFRAMES_PER_SHOT = 2` 对应默认 `first + mid` 两张代表图。
- embedding 默认策略为后处理：
  - 首轮 ingest 只写入 `frames` 与 `pending_backfill` 状态，不阻塞等待 Gemini。
  - 后处理任务再批量补齐 `Frame.embedding`，失败帧保留 `embedding_status=failed` 供重试。
- 长音频 ASR 默认采用 `VAD + stream`：
  - `node` 后端默认走 `ffmpeg + Silero VAD + sherpa-onnx SenseVoice`
  - 检出语音段后立即识别，不再整段音频二次回读
  - `python` 后端保留为兼容回退路径
