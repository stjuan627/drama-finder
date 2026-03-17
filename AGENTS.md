# AGENTS.md

## 项目目标
- 本项目是一个中文剧集截图定位系统。
- 第一版目标是：导入单部剧整季视频后，用户上传一张截图，系统返回对应的 `剧集 + 时间点`。
- 第一版优先完成后端闭环，再补最小可演示页面。

## 当前定稿方案
- 技术栈固定为 `Python + FastAPI + PostgreSQL + pgvector + Redis/RQ`。
- 入库采用 `API 提交任务 + 本地后台 worker 离线处理`。
- 媒体文件和中间产物固定落在本地文件系统，不接对象存储。
- 文本来源只使用本地 `ASR`，默认首选 `faster-whisper`。
- 第一版不做 OCR，不做画面文字检索。
- 检索结构固定为双层：
  - `scene/shot` 负责主召回
  - `1fps frame` 负责局部精定位

## 事实来源与输入约定
- 剧集基础元数据不能依赖文件名自动猜测。
- 每部剧必须提供一个 `manifest.yaml` 或 `manifest.json` 作为唯一事实源。
- manifest 至少包含：
  - `series_id`
  - `series_title`
  - `season_label`
  - `language`
  - `video_root`
  - `episodes[]`
- `episodes[]` 每项至少包含：
  - `episode_id`
  - `episode_no`
  - `title`
  - `filename`
- 文件命名约定只用于校验，不作为主数据来源。

## 入库流程约定
- `POST /ingest/episode` 接收 `series_id + episode_id`，不直接上传大文件。
- 单集入库固定阶段为：
  1. 加载 manifest
  2. 定位视频文件
  3. `ffmpeg` 抽音轨
  4. 本地 ASR
  5. `PySceneDetect` 切 shot
  6. `1fps` 抽帧
  7. 代表帧选择
  8. `Gemini 3 Flash` 做 scene 合并与摘要
  9. `gemini-embedding-2-preview` 生成 scene/frame embedding
  10. 写入数据库
- 入库按 `episode` 级幂等覆盖处理；同一集重跑时替换旧索引和旧元数据。
- 失败任务保留中间产物，不做媒体文件回滚。

## 数据与存储约定
- 主库固定为 `PostgreSQL + pgvector`。
- 首批核心表固定为：
  - `series`
  - `episodes`
  - `ingest_jobs`
  - `shots`
  - `scenes`
  - `frames`
- `shots` 作为中间结构入库，不能省略，便于评测和问题排查。
- 本地文件目录固定为：
  - `data/series/<series_id>/source/`
  - `data/series/<series_id>/audio/`
  - `data/series/<series_id>/frames/`
  - `data/series/<series_id>/artifacts/`

## 检索与接口约定
- `POST /search/image` 是第一优先级主接口。
- 检索流程固定为：
  1. 先查 `scene` topK
  2. 再在候选 scene 时间窗内查 `frame` topK
  3. 最后做精排并返回 `top1 + top3`
- 第一版精排至少包含：
  - embedding 相似度
  - ASR 文本重合度
  - 邻近帧连续性
- `POST /search/text` 保留，但优先级低于截图检索。
- 未命中时必须返回显式低置信状态，不能伪造高分结果。

## 开发顺序
1. 先完成 `manifest + schema + ingest_jobs`。
2. 再完成本地 worker，打通 `ASR + shot detection + frame extraction`。
3. 然后接入 Gemini scene 合并与 embedding。
4. 最后实现 `search/image`、`search/text`、评测脚本和演示页。

## 验收标准
- 单集视频能稳定入库并生成可查询的 `scene` 和 `frame` 记录。
- 截图查询能返回 `top1` 与 `top3` 候选。
- 主方案与纯 `1fps frame` 基线必须可同场评测。
- 整季评测目标：
  - `Top1 命中正确 scene >= 70%`
  - `Top5 命中正确 scene >= 90%`
  - `时间误差中位数 <= 5 秒`

## 实施规则
- 改动实现前，优先对齐本文件与 [docs/general-plan.md](/home/james/works/projects/drama-finder/docs/general-plan.md)。
- 如出现冲突，以 `docs/general-plan.md` 的最新方案为准，并同步更新本文件。
- 新增设计若会改变技术栈、数据来源、索引层次、主流程或验收标准，必须先更新文档再实现。
- 项目使用 git 管理。
- 每完成一项独立任务或任务板状态从 `IN_PROGRESS` 进入 `DONE`，都应立即提交一次，保持历史可追溯。
