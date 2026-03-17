# 入库任务状态机规格

## 状态枚举
- `queued`
- `running`
- `failed`
- `completed`

## 阶段枚举
- `queued`
- `manifest`
- `audio_extraction`
- `asr`
- `shot_detection`
- `frame_extraction`
- `representative_frames`
- `scene_merge`
- `embeddings`
- `persist`
- `completed`
- `failed`

## 生命周期
1. `POST /ingest/episode` 创建任务，状态为 `queued`。
2. 成功进入 Redis/RQ 后，worker 取到任务并改为 `running`。
3. pipeline 每完成一个阶段，更新 `current_stage` 与 `progress_current`。
4. 任一阶段抛出异常，任务改为 `failed`。
5. 全部阶段成功，任务改为 `completed`。

## 并发规则
- 同一 `(series_pk, episode_pk)` 最近任务为 `queued/running` 时，不再新建重复任务。
- 当前实现不支持 `force_reingest`。
- worker 侧不做同 episode 并发锁；幂等覆盖依赖 API 层和人工控制。

## 错误处理
- 入队失败：
  - 直接抛错给 API
  - 不在当前任务状态机内增加额外阶段枚举
- pipeline 失败：
  - `status = failed`
  - `error_message = 异常消息`
- 失败时保留中间产物，不自动回滚媒体文件。

## 计数字段
- 当前实现不在 `ingest_jobs` 表中单独冗余 `shot_count/scene_count/frame_count`，产物统计写入 `artifacts`。

## 时间字段
- `started_at` 在 worker 真正开始时写入。
- `finished_at` 在成功或失败时写入。
