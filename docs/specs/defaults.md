# 默认值规范

## 运行默认值
- `SEGMENT_TARGET_MIN_SECONDS = 5`
- `SEGMENT_TARGET_MAX_SECONDS = 15`
- `SHOT_KEYFRAMES_PER_SHOT = 3`
- `INTRO_OUTRO_SCAN_WINDOW_SECONDS = 300`
- `INTRO_OUTRO_MIN_REPEAT_EPISODES = 3`
- `GLOBAL_FRAME_INDEX_ENABLED = false`
- `LOCAL_FRAME_FALLBACK_FPS = 0.5`
- `JOB_TIMEOUT_SECONDS = 7200`
- `JOB_RETRY_COUNT = 1`
- `LOW_CONFIDENCE_THRESHOLD = 0.35`
- `INGEST_SKIP_EMBEDDINGS = false`

## 模型默认值
- `gemini_embedding_model = gemini-embedding-2-preview`
- `gemini_scene_model = gemini-3-flash-preview`
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
- `GLOBAL_FRAME_INDEX_ENABLED = false` 表示全库不默认生成高密度 frame 检索索引。
- `LOCAL_FRAME_FALLBACK_FPS` 只用于命中候选区间后的局部细化，不用于全库主检索。
