# 数据库 Schema 规格

## 总体约束
- 主库固定为 `PostgreSQL + pgvector`
- 所有时间戳字段单位固定为秒，类型使用 `float`
- 所有 embedding 维度固定为 `3072`
- 第一版主键统一使用 `uuid`

## 核心表
- `series`
- `episodes`
- `ingest_jobs`
- `shots`
- `frames`

## series
- 主键：`id uuid`
- 唯一键：`series_id`

## episodes
- 主键：`id uuid`
- 外键：`series_pk -> series.id`
- 唯一键：
  - `(series_pk, episode_id)`
  - `(series_pk, episode_no)`

## ingest_jobs
- 主键：`id uuid`
- 外键：
  - `series_pk -> series.id`
  - `episode_pk -> episodes.id`
- 关键字段：
  - `status`
  - `current_stage`
  - `progress_current`
  - `progress_total`
  - `attempt`
  - `error_message`
  - `artifacts`

## shots
- 主键：`id uuid`
- 外键：`episode_pk -> episodes.id`
- 字段：
  - `shot_index int not null`
  - `start_ts float not null`
  - `end_ts float not null`
  - `representative_frame_paths jsonb not null`
  - `raw_metadata jsonb not null`
- 说明：
  - 当前实现默认写入 `first + mid` 两张代表图
  - `shot` 对应的 `asr_text` 当前保存在 `raw_metadata.asr_text`

## frames
- 主键：`id uuid`
- 外键：
  - `episode_pk -> episodes.id`
  - `shot_pk -> shots.id`
- 字段：
  - `frame_index int not null`
  - `frame_ts float not null`
  - `image_path text not null`
  - `context_asr_text text not null`
  - `embedding vector(3072) null`
  - `raw_metadata jsonb not null`
- 说明：
  - 默认按 `3s` 一帧抽样
  - `raw_metadata.index_excluded=true` 的帧不参与主检索

## 索引约定
- `series.series_id`
- `episodes.series_pk`
- `ingest_jobs.series_pk`
- `ingest_jobs.episode_pk`
- `shots.episode_pk`
- `frames.episode_pk`

## 幂等覆盖规则
- 同一 `episode_pk` 重新入库时，先删除旧 `shots/frames`
- `series` 与 `episodes` 为上游事实，不在重跑时删除
- `ingest_jobs` 保留历史记录，不覆盖历史任务行

## 当前实现说明
- 历史 `scenes/segments` 结构可能仍存在于数据库中，但不再参与当前主链路。
- 当前主索引层是 `frames` 与 `shots(raw_metadata.asr_text)`。
