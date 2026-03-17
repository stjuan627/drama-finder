# API 规格

## 公共约定
- API 返回 JSON
- 当前不做鉴权
- 当前目标输出是“可信区间”，不是秒级点位

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
  - `SearchResponse`

## `POST /search/text`
- 请求体：
  - `query: string`
  - `limit: int = 3`
- 成功响应：
  - `200`
  - `SearchResponse`

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

## `SearchResponse`
- `hits: SearchHit[]`
- `low_confidence: boolean`

## `SearchHit`
- `series_id: string`
- `episode_id: string`
- `matched_start_ts: float`
- `matched_end_ts: float`
- `score: float`
- `segment_summary: string | null`
- `evidence_images: string[]`
- `evidence_text: string[]`

## 兼容说明
- 现有代码仍保留 `matched_ts / scene_start_ts / scene_end_ts` 过渡结构。
- 后续接口应迁移到区间字段为主，不再把单点时间戳作为主结果。
