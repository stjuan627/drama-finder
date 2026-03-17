# API 规格

## 公共约定
- API 前缀：`/api/v1`
- 返回格式：JSON
- 当前不做鉴权

## `GET /healthz`
- 响应：
  - `200`
  - `{ "status": "ok" }`

## `POST /ingest/episode`
- 请求体：
  - `manifest_path: string`
  - `series_id: string`
  - `episode_id: string`
- 成功响应：
  - `202`
  - `IngestJobRead`
- 错误：
  - `400` manifest 不合法或找不到 episode

## `GET /ingest/{job_id}`
- 成功响应：
  - `200`
  - `IngestJobRead`
- 错误：
  - `404` 任务不存在

## `POST /search/image`
- 表单字段：
  - `file: image/*`
- 成功响应：
  - `200`
  - `SearchImageResponse`
- 错误：
  - `400` 非图片文件
  - `400` 空文件

## `POST /search/text`
- 请求体：
  - `query: string`
  - `limit: int = 3`
- 成功响应：
  - `200`
  - `SearchImageResponse`

## `IngestJobRead`
- `id: uuid`
- `series_pk: uuid`
- `episode_pk: uuid`
- `status: JobStatus`
- `current_stage: JobStage | null`
- `progress_current: int`
- `progress_total: int`
- `attempt: int`
- `error_message: string | null`
- `started_at: datetime | null`
- `finished_at: datetime | null`
- `artifacts: object`

## `SearchImageResponse`
- `hits: SearchHit[]`
- `low_confidence: boolean`

## `SearchHit`
- `series_id: string`
- `episode_id: string`
- `matched_ts: float`
- `scene_start_ts: float | null`
- `scene_end_ts: float | null`
- `score: float`
- `scene_summary: string | null`
- `evidence_frames: string[]`
- `evidence_text: string[]`
