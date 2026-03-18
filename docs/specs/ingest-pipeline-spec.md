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
  - 默认模型：`iic/SenseVoiceSmall`
  - 默认设备：`CPU`
  - 默认量化：`int8`
  - 先用 `VAD` 做语音段检测，再按流式 chunk 逐段送入 ASR，避免整段长音频一次性进模型
  - 输出：`artifacts/asr_segments.json`
  - 结构：`[{start, end, text}]`
4. `shot_detection`
  - 优先使用 `PySceneDetect`
  - 输出：`artifacts/shots.json`
5. `shot_keyframes`
  - 每个 shot 固定生成 `first / mid` 代表图
  - 用于人工质检与文本检索证据
6. `frame_extraction`
  - 固定每 `3s` 抽一帧
  - 输出：`artifacts/indexed_frames.json`
7. `embeddings`
  - 只对图片路径的 `frame` 生成主 embedding
  - 默认允许拆成后处理，不阻塞首轮入库
8. `persist`
  - 先删旧 `shots/frames`
  - 再写新记录

## 关键规则
- 全库不默认生成 `1fps` 检索索引，第一版固定 `3s` 一帧。
- `frames/` 是图片主索引目录。
- `shots` 负责底层切分事实与代表图质检，不承担图片主索引职责。
- 片头片尾通过 manifest 配置为索引排除区间，但返回时间戳仍沿用原始视频时间轴。
- 已人工验证当前 shot 切分质量可接受，默认代表图策略固定为 `first + mid`。

## 当前实现说明
- 当前代码应以 `frames` 作为图片主索引，以 `ASR` 文本作为文本主路径。
- 入库重跑的主链路覆盖对象为 `shots/frames`，`segments/scenes` 如仍存在仅保留历史兼容，不再作为主流程对象。
