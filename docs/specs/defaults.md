# 默认值规范

## 运行默认值
- `FRAME_EXTRACTION_FPS = 1`
- `FRAME_HASH_SIZE = 16`
- `SCENE_TOP_K = 10`
- `FRAME_TOP_K = 20`
- `TEXT_TOP_K = 3`
- `ASR_CONTEXT_WINDOW_SECONDS = 5`
- `REPRESENTATIVE_FRAMES_PER_SHOT = 3`
- `JOB_TIMEOUT_SECONDS = 7200`
- `JOB_RETRY_COUNT = 1`
- `LOW_CONFIDENCE_THRESHOLD = 0.35`

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
