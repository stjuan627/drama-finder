# 入库 Pipeline 规格

## 入口
- 输入：`manifest_path`、`series_id`、`episode_id`
- 事实源：manifest
- 输出：
  - 本地媒体产物
  - `shots/frames`
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
   - 使用 `SenseVoice Small ONNX`
   - 默认后端：`Node.js + sherpa-onnx`
  - 默认模型：`iic/SenseVoiceSmall`
  - 默认设备：`CPU`
  - 默认 CPU 线程：`2`
   - 默认量化：`int8`
   - 先用 `Silero VAD` 做小窗检测，再按流式 chunk 逐段送入 ASR，避免整段长音频一次性进模型
   - 可选开启 `ct-punc-c` 风格的离线标点恢复；开启后只改写文本，不重切时间戳
   - 输出：`artifacts/asr_segments.json`
   - 基础结构：`[{start, end, text}]`
   - 开启标点恢复时可额外包含 `raw_text` 字段，用于保留无标点原文
4. `shot_detection`
  - 优先使用 `PySceneDetect`
  - 输出：`artifacts/shots.json`
5. `frame_extraction`
  - 固定每 `3s` 抽一帧
  - 输出：`artifacts/indexed_frames.json`
6. `embeddings`
  - 只对图片路径的 `frame` 生成主 embedding
  - 默认允许拆成后处理，不阻塞首轮入库
7. `persist`
  - 先删旧 `shots/frames`
  - 再写新记录

## 关键规则
- 全库不默认生成 `1fps` 检索索引，第一版固定 `3s` 一帧。
- `frames/` 是图片主索引目录。
- `shots` 只负责底层切分事实，不承担图片主索引职责。
- 片头片尾通过 manifest 配置为索引排除区间，但返回时间戳仍沿用原始视频时间轴。
- 已人工验证当前 shot 切分质量可接受。

## 当前实现说明
- 当前代码应以 `frames` 作为图片主索引，以 `ASR` 文本作为文本主路径。
- 入库重跑的主链路覆盖对象为 `shots/frames`，`segments/scenes` 如仍存在仅保留历史兼容，不再作为主流程对象。
- episode 级重跑会重新写入 `artifacts/asr_segments.json`，并替换该集旧的 `shots/frames` 文本内容。
