# 入库任务状态机规格

## 状态枚举
- `queued`
- `running`
- `failed`
- `completed`

## 目标阶段枚举
- `manifest`
- `audio_extraction`
- `asr`
- `shot_detection`
- `frame_extraction`
- `embeddings`
- `persist`

## 生命周期
1. `POST /ingest/episode` 创建任务，状态为 `queued`。
2. 成功进入 Redis/RQ 后，worker 取到任务并改为 `running`。
3. pipeline 每完成一个阶段，更新 `current_stage` 与 `progress_current`。
4. 任一阶段抛出异常，任务改为 `failed`。
5. 全部阶段成功，任务改为 `completed`。

## 并发规则
- 同一 `(series_pk, episode_pk)` 最近任务为 `queued/running` 时，不再新建重复任务。
- worker 侧不做同 episode 并发锁；幂等覆盖依赖 API 层和人工控制。

## 错误处理
- 失败时保留中间产物，不自动回滚媒体文件。
- 正式方案中，embedding 失败不应迫使整条入库重跑；应允许拆成后处理任务。

## 计数字段
- `ingest_jobs` 可将 `shot_count / frame_count` 记录到 `artifacts`。

## 当前实现说明
- 当前数据库阶段枚举仍保留部分历史值，但代码层主路径已经切到 `frame_extraction`。
- 后续如需要清理历史命名，应通过显式迁移完成枚举值收口。
