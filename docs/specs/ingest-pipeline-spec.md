# 入库 Pipeline 规格

## 入口
- 输入：`manifest_path`、`series_id`、`episode_id`
- 事实源：manifest
- 输出：
  - 本地媒体产物
  - `shots/segments`
  - `ingest_jobs` 状态更新

## 目录结构
- `data/series/<series_id>/<episode_id>/source/`
- `data/series/<series_id>/<episode_id>/audio/`
- `data/series/<series_id>/<episode_id>/frames/`
- `data/series/<series_id>/<episode_id>/artifacts/`

## 阶段顺序
1. `manifest`
  - 读取 manifest
  - 校验 episode 是否存在
  - 定位源视频路径
2. `audio_extraction`
  - 使用 `ffmpeg` 抽取单声道 `16k wav`
3. `asr`
  - 使用 `faster-whisper`
  - 输出：`artifacts/asr_segments.json`
  - 结构：`[{start, end, text}]`
4. `intro_outro_trim`
  - 基于跨集重复片段检测识别片头片尾
  - 当前允许先跳过，后续作为正式阶段补齐
5. `shot_detection`
  - 优先使用 `PySceneDetect`
  - 输出：`artifacts/shots.json`
6. `shot_keyframes`
  - 每个 shot 生成 `start / mid / end` 代表图
  - 用于人工质检、segment 表示与检索证据
7. `segment_build`
  - 将连续 shot 合并为 `5s - 15s` 的可信区间
8. `segment_summary`
  - 使用 Gemini 为 segment 生成摘要或做合并复核
  - Gemini 返回空结果时必须回退到本地默认规则
9. `embeddings`
  - 只对 `segment` 生成主 embedding
  - 默认允许拆成后处理，不阻塞首轮入库
10. `persist`
  - 先删旧 `shots/segments`
  - 再写新记录

## 关键规则
- 全库不默认生成 `1fps` 检索索引。
- `frames/` 可继续保留为调试或局部回扫辅助，但不再作为主检索层。
- `segment` 目标是可读区间，不是尽量短的镜头切片。
- 片头片尾必须在正式检索库中被裁掉或显式标记为可忽略。

## 当前实现说明
- 当前代码已真实产出 `shots/scenes/frames`，属于过渡结果。
- 后续开发应优先把当前 `scene` 迁移为 `segment`，并把 `frame` 从主索引降级为辅助结构。
