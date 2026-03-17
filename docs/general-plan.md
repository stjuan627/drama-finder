# 中文剧集片段定位系统 V1 方案

## 摘要
- 第一版目标从“秒级定位”调整为“可信区间定位”。
- 目标体验是：输入截图或台词，返回 `剧集 + 时间区间`，例如 `ep01 00:30 - 00:40`。只要区间可信且命中正确剧情片段，即视为可接受。
- 检索主单位从 `1fps frame` 改为 `segment`，由多个连续 `shot` 组成，默认长度控制在 `5s - 15s`。
- `shot` 仍然是底层切分事实，`segment` 才是主检索、主存储、主返回单位。
- 全库不再默认维护高密度 `1fps` 向量索引。全库只保留 `shot/segment` 级代表图与文本；局部高频扫描作为后续可选增强。

## 核心设计
1. 入库与切分
- 每集固定流程为：`加载 manifest -> 音轨提取 -> ASR -> 片头片尾识别与裁剪 -> shot detection -> shot 代表图生成 -> segment 合并 -> 可选 scene summary -> 可选 embedding -> 写库`。
- `shot detection` 继续由本地方案负责，首选 `PySceneDetect`。
- 每个 `shot` 固定保存 `start / mid / end` 三张代表图，用于质检、人工确认和后续合并。
- `segment` 由相邻 `shot` 合并得到，目标是保证：
  - 语义连续
  - 时长可读
  - 返回给用户时能作为“可信区间”

2. 片头片尾处理
- 优先使用本地重复片段检测，不依赖大模型。
- 基本策略是：比较同一部剧多集的前后固定时间窗，寻找跨集重复的连续区间，识别为片头/片尾。
- 片头片尾裁剪发生在 shot/segment 构建之前，避免它们污染检索库。
- Gemini 仅在候选边界不稳定时作为复核，不作为主检测器。

3. 检索结构
- 主检索入口改为 `segment`，不再依赖全库 `1fps frame` 检索。
- `shot` 是段内细粒度结构，不直接作为默认返回单位。
- 默认检索流程：
  1. 查询图片或文本生成 query embedding
  2. 查询 `segment` topK
  3. 对候选 `segment` 做轻量精排
  4. 返回可信区间和证据图/证据文本
- 后续如需更细定位，可在命中 `segment` 后局部回扫 `shot` 或低频 `frame`，但这不是 V1 主链路。

4. 成本与准确率策略
- 默认不再全库维护 `1fps frame embedding`。
- 默认优先做：
  - `segment embedding`
  - `shot 代表图`
  - `ASR 文本`
- embedding 生成与入库主流程解耦，允许先完成入库，再做后处理批量生成。
- 当前为尽快验证真实链路，允许本地启用 `INGEST_SKIP_EMBEDDINGS=true`；正式检索前再恢复 segment 级 embedding。

## 数据模型与接口
- 核心事实单位：
  - `series`
  - `episodes`
  - `ingest_jobs`
  - `shots`
  - `segments`
- `frames` 只保留为可选辅助产物，不再作为默认主索引。
- `shots` 保存：
  - `start_ts`
  - `end_ts`
  - `start_frame_path`
  - `mid_frame_path`
  - `end_frame_path`
  - `asr_text`
- `segments` 保存：
  - `start_ts`
  - `end_ts`
  - `summary`
  - `asr_text`
  - `representative_frame_paths`
  - `embedding`
  - `shot_indexes`
- 查询接口的目标返回结构应以区间为主，而不是单点时间戳：
  - `matched_start_ts`
  - `matched_end_ts`
  - `score`
  - `evidence_frames`
  - `evidence_text`

## 测试与验收
- 入库验收：
  - 单集视频能稳定产出 `shots` 与 `segments`
  - `shot` 有代表图
  - 片头片尾可被识别并剔除或显式标记
- 检索验收：
  - 返回结果必须是可信区间
  - 允许低精度，不要求秒级
  - 首批目标是“区间正确”优先于“秒级接近”
- 当前建议验收口径：
  - `Top1 命中正确 segment >= 70%`
  - `Top5 命中正确 segment >= 90%`
  - 返回区间覆盖人工标注剧情片段

## 当前实现与目标差异
- 当前代码已真实跑通 `wufulinmen / ep01` 入库闭环，但仍是过渡状态。
- 当前真实产物里：
  - `shots` 可用
  - `frames` 仍然存在，属于历史过渡设计
  - `scenes` 当前仍可能退化为 `1 shot = 1 scene`
- 后续开发应优先把当前 `scene/frame` 过渡实现迁移到 `shot/segment` 正式结构，不再扩大 `frame` 的责任边界。
