# 数据库 Schema 规格

## 总体约束
- 主库固定为 `PostgreSQL + pgvector`。
- 所有时间戳字段单位固定为“秒”，类型使用 `float`。
- 所有 embedding 维度固定为 `3072`，引用 [defaults.md](/home/james/works/projects/drama-finder/docs/specs/defaults.md)。
- 第一版主键统一使用 `uuid`。
- 第一版核心表固定为：
  - `series`
  - `episodes`
  - `ingest_jobs`
  - `shots`
  - `scenes`
  - `frames`

## series
- 主键：`id uuid`
- 唯一键：`series_id`
- 字段：
  - `series_id varchar(64) not null`
  - `title varchar(255) not null`
  - `season_label varchar(128) null`
  - `language varchar(32) not null`
  - `manifest_path varchar(1024) not null`
  - `created_at timestamptz not null`
  - `updated_at timestamptz not null`

## episodes
- 主键：`id uuid`
- 外键：`series_pk -> series.id`
- 唯一键：`(series_pk, episode_id)`
- 字段：
  - `episode_id varchar(64) not null`
  - `episode_no int not null`
  - `title varchar(255) not null`
  - `filename varchar(512) not null`
  - `video_path varchar(1024) not null`
  - `created_at timestamptz not null`
  - `updated_at timestamptz not null`

## ingest_jobs
- 主键：`id uuid`
- 外键：
  - `series_pk -> series.id`
  - `episode_pk -> episodes.id`
- 字段：
  - `status enum(jobstatus) not null`
  - `manifest_path varchar(1024) not null`
  - `current_stage enum(jobstage) null`
  - `progress_current int not null`
  - `progress_total int not null`
  - `attempt int not null`
  - `error_message text null`
  - `started_at timestamptz null`
  - `finished_at timestamptz null`
  - `artifacts jsonb not null`
  - `created_at timestamptz not null`
  - `updated_at timestamptz not null`

## shots
- 主键：`id int`
- 外键：`episode_pk -> episodes.id`
- 字段：
  - `shot_index int not null`
  - `start_ts float not null`
  - `end_ts float not null`
  - `representative_frame_paths jsonb not null`
  - `raw_metadata jsonb not null`
  - `created_at timestamptz not null`
  - `updated_at timestamptz not null`

## scenes
- 主键：`id int`
- 外键：`episode_pk -> episodes.id`
- 字段：
  - `scene_index int not null`
  - `start_ts float not null`
  - `end_ts float not null`
  - `summary text null`
  - `asr_text text not null`
  - `representative_frame_paths jsonb not null`
  - `embedding vector(3072) null`
  - `raw_metadata jsonb not null`
  - `created_at timestamptz not null`
  - `updated_at timestamptz not null`

## frames
- 主键：`id int`
- 外键：
  - `episode_pk -> episodes.id`
  - `shot_pk -> shots.id`
  - `scene_pk -> scenes.id`
- 字段：
  - `frame_index int not null`
  - `frame_ts float not null`
  - `image_path varchar(1024) not null`
  - `context_asr_text text not null`
  - `embedding vector(3072) null`
  - `raw_metadata jsonb not null`
  - `created_at timestamptz not null`
  - `updated_at timestamptz not null`

## 索引约定
- `series.series_id`
- `episodes.series_pk`
- `ingest_jobs.series_pk`
- `ingest_jobs.episode_pk`
- `shots.episode_pk`
- `scenes.episode_pk`
- `frames.episode_pk`
- `frames.shot_pk`
- `frames.scene_pk`

## 幂等覆盖规则
- 同一 `episode_pk` 重新入库时，先删除旧 `frames`、`scenes`、`shots`，再写入新结果。
- `series` 与 `episodes` 为上游事实，不在重跑时删除。
- `ingest_jobs` 保留历史记录，不覆盖历史任务行。
