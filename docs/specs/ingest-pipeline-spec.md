# 入库 Pipeline 规格

## 入口
- 输入：`manifest_path`、`series_id`、`episode_id`
- 事实源：manifest
- 输出：
  - 本地媒体产物
  - `shots/scenes/frames`
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
  - 输出：`audio/<episode_id>.wav`
3. `asr`
  - 使用 `faster-whisper`
  - 输出：`artifacts/<episode_id>/transcript.json`
  - 结构：`[{start, end, text}]`
4. `shot_detection`
  - 优先使用 `PySceneDetect`
  - 失败或不可用时退化为单 shot 覆盖整集
  - 输出：`artifacts/<episode_id>/shots.json`
5. `frame_extraction`
  - 使用 `ffmpeg fps=1`
  - 输出：`frames/<episode_id>/frame_%06d.jpg`
6. `representative_frames`
  - 为每个 shot 绑定代表帧
7. `scene_merge`
  - 基于 shot 和 ASR 做规则合并
  - 使用 Gemini 生成 scene 摘要
8. `embeddings`
  - scene 级：对 `summary + asr_text + 代表帧描述` 生成 embedding
  - frame 级：对 `context_asr_text + 当前帧描述` 生成 embedding
9. `persist`
  - 先删旧 `frames/scenes/shots`
  - 再写新记录

## 规则合并场景
- 满足任一条件时切新 scene：
  - 当前 scene 时长超过 `90` 秒
  - 相邻 shot 间没有桥接 transcript

## 代表帧
- shot 代表帧当前默认取 1 张。
- scene 代表帧从所属 shot 代表帧中截取最多 3 张。

## 幂等
- 当前实现每次执行都会重建该集产物文件。
- 重新入库不会删除历史 job，但会覆盖该集的 `shots/scenes/frames`。
