# 中文剧集片段定位系统 V1 方案

## 摘要
- 第一版目标从“秒级定位”调整为“可信区间定位”。
- 目标体验是：输入截图或台词，返回 `剧集 + 时间区间`，例如 `ep01 00:30 - 00:40`。只要区间可信且命中正确剧情片段，即视为可接受。
- 第一版不再引入 `scene/segment` 作为主检索层。
- 图片路径固定走 `3 秒一截图` 的低频 `frame` 索引，约等于 `0.33fps`。
- 文本路径固定走 `ASR` 文本，直接基于时间对齐后的文本片段或 `shot` 聚合文本返回区间。
- `ASR` 实现层定稿为 `SenseVoice Small ONNX`，默认使用量化模型并优先面向 `CPU`。

## 核心设计
1. 入库与切分
- 每集固定流程为：`加载 manifest -> 音轨提取 -> ASR -> shot detection -> shot 代表图生成 -> 3 秒采样 frame -> 可选 embedding -> 写库`。
- `shot detection` 继续由本地方案负责，首选 `PySceneDetect`。
- `ASR` 首选 `SenseVoice Small ONNX`，默认配置为：
  - 模型：`iic/SenseVoiceSmall`
  - 推理：`ONNX`
  - 量化：开启
  - 设备：`CPU`
  - CPU 线程：默认 `2`
- 为避免长音频整段送入 ASR 造成内存峰值过高，默认链路改为：
  - 先做 `VAD`
  - 再按流式 chunk 推进
  - 最后按语音段逐段调用 `SenseVoice Small ONNX`
- 第一版继续保持 `ASR` 产物结构为 `[{start, end, text}]`，不改入库和检索下游契约。
- 每个 `shot` 默认保存 `first / mid` 两张代表图，用于质检、人工确认和文本命中后的证据展示。
- 主检索层拆成两条：
  - 图片检索：`frame`
  - 文本检索：`ASR text`

2. 片头片尾处理
- 第一版不做自动检测。
- 片头片尾由 `manifest` 显式配置，例如固定 `intro_duration_seconds=120`、`outro_duration_seconds=120`。
- 它们可以不进入主索引，但时间轴仍然保持原视频绝对时间，不做时间平移。
- 也就是说，命中结果里的时间戳始终对应源视频真实时间。

3. 检索结构
- 图片检索入口改为低频 `frame`，固定 `3s` 一帧。
- 文本检索入口改为 `ASR` 文本，不再引入 `scene/segment` 中间层。
- `shot` 继续保留为底层切分事实与质检结构，但不是图片主索引。
- 默认检索流程：
  1. 图片查询生成 query embedding
  2. 查询 `frame` topK
  3. 返回 `frame_ts ~ frame_ts+3s` 的候选区间
  4. 文本查询直接匹配 `ASR` 文本并返回对应区间
- 后续如需更细定位，可在命中 `frame` 后局部回扫相邻帧或对应 `shot`，但这不是 V1 主链路。

4. 成本与准确率策略
- 默认不做高密度 `1fps frame embedding`。
- 默认优先做：
  - `3s frame embedding`
  - `shot first/mid` 代表图
  - `ASR` 文本
- embedding 主要服务图片路径；文本路径优先依赖 `ASR` 文本本身。
- 当前为尽快验证真实链路，允许本地启用 `INGEST_SKIP_EMBEDDINGS=true`。
- `ASR` 路径优先保证 `CPU` 速度与部署简单性，不再以 `faster-whisper` 作为默认实现。

## 数据模型与接口
- 核心事实单位：
  - `series`
  - `episodes`
  - `ingest_jobs`
  - `shots`
  - `frames`
- `frames` 现在是图片主索引，不再只是辅助产物。
- `shots` 保存：
  - `start_ts`
  - `end_ts`
  - `first_frame_path`
  - `mid_frame_path`
  - `asr_text`
- `frames` 保存：
  - `frame_ts`
  - `image_path`
  - `context_asr_text`
  - `embedding`
- 查询接口的目标返回结构应以区间为主，而不是单点时间戳：
  - `matched_start_ts`
  - `matched_end_ts`
  - `score`
  - `evidence_images`
  - `evidence_text`

## 测试与验收
- 入库验收：
  - 单集视频能稳定产出 `shots` 与 `frames`
  - `shot` 有代表图
  - `manifest` 中的片头片尾配置能影响索引排除范围
- 检索验收：
  - 返回结果必须是可信区间
  - 允许低精度，不要求秒级
  - 首批目标是“区间正确”优先于“镜头语义分段”
- 当前建议验收口径：
  - `Top1 命中正确区间 >= 70%`
  - `Top5 命中正确区间 >= 90%`
  - 返回区间覆盖人工标注剧情片段

## 当前实现与目标差异
- 当前代码已真实跑通 `wufulinmen / ep01` 入库闭环，接下来主链改为 `frame + ASR text`。
- 已人工验证 `ep01` 的 shot 质检结果，当前切分质量可接受。
- 当前经验结论是：大多数 shot 用 `first + mid` 两张图已经足够表达画面连续性。
- 当前真实产物里：
  - `shots` 可用
  - `frames` 需要恢复为图片主索引
  - `segments/scenes` 不再继续扩大责任边界
- 当前 `ASR` 代码实现仍是历史方案，后续需要切换到 `SenseVoice Small ONNX`，但下游接口保持不变。
- 后续开发应继续围绕 `frame + ASR text` 收敛，不再引入 `scene/segment` 主层。
