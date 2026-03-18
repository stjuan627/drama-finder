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
- `INGEST_SKIP_EMBEDDINGS = false`

## 模型默认值
- `gemini_embedding_model = gemini-embedding-2-preview`
- `embedding_dimensions = 3072`
- `asr_model_name = small`
- `asr_device = auto`
- `asr_compute_type = int8`

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
