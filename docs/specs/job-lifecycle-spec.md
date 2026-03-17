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
- `intro_outro_trim`
- `shot_detection`
- `shot_keyframes`
- `segment_build`
- `segment_summary`
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
- Gemini 返回空结构时不允许直接中断任务，应优先回退到本地默认规则。
- 正式方案中，embedding 失败不应迫使整条入库重跑；应允许拆成后处理任务。

## 计数字段
- `ingest_jobs` 可将 `shot_count / segment_count / frame_count` 记录到 `artifacts`。

## 当前实现说明
- 当前代码阶段枚举仍保留 `frame_extraction / representative_frames / scene_merge` 等旧命名。
- 后续实现应逐步迁移到本文件描述的 `segment` 阶段语义。
