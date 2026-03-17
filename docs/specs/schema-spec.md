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
- `segments`

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

## segments
- 主键：`id uuid`
- 外键：`episode_pk -> episodes.id`
- 字段：
  - `segment_index int not null`
  - `start_ts float not null`
  - `end_ts float not null`
  - `summary text null`
  - `asr_text text not null`
  - `representative_frame_paths jsonb not null`
  - `shot_indexes jsonb not null`
  - `embedding vector(3072) null`
  - `raw_metadata jsonb not null`

## 可选辅助表
- `frames`
  - 仅用于局部回扫或调试
  - 不是正式 V1 主索引必需表

## 索引约定
- `series.series_id`
- `episodes.series_pk`
- `ingest_jobs.series_pk`
- `ingest_jobs.episode_pk`
- `shots.episode_pk`
- `segments.episode_pk`

## 幂等覆盖规则
- 同一 `episode_pk` 重新入库时，先删除旧 `shots/segments`
- `series` 与 `episodes` 为上游事实，不在重跑时删除
- `ingest_jobs` 保留历史记录，不覆盖历史任务行

## 当前实现说明
- 当前代码中的 `Segment` 模型兼容映射到历史 `scenes` 表。
- `frames` 仍然存在于 schema 中，但不再参与默认主检索链路。
