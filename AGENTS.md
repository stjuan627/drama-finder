# AGENTS.md

## 项目目标
- 本项目是一个中文剧集片段定位系统。
- 第一版目标是：导入单部剧整季视频后，用户上传截图或输入台词，系统返回对应的 `剧集 + 时间区间`。
- 当前接受低精度但高可信结果，例如 `ep01 00:30 - 00:40`。
- 第一版优先完成后端闭环，再补最小可演示页面。

## 当前定稿方案
- 技术栈固定为 `Python + FastAPI + PostgreSQL + pgvector + Redis/RQ`。
- 入库采用 `API 提交任务 + 本地后台 worker 离线处理`。
- 媒体文件和中间产物固定落在本地文件系统，不接对象存储。
- 文本来源只使用本地 `ASR`。
- 第一版不做 OCR，不做画面文字检索。
- 检索结构固定为：
  - `shot` 负责底层切分事实
  - `segment` 负责主召回和主返回
  - 全库不默认维护 `1fps frame` 主索引

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
- 单集入库目标阶段为：
  1. 加载 manifest
  2. 定位视频文件
  3. `ffmpeg` 抽音轨
  4. 本地 ASR
  5. 本地片头片尾检测与裁剪
  6. `3s` 抽帧
  7. `gemini-embedding-2-preview` 可选生成 frame embedding
  8. 写入数据库
- 入库按 `episode` 级幂等覆盖处理；同一集重跑时替换旧索引和旧元数据。
- 失败任务保留中间产物，不做媒体文件回滚。
- 当前允许跳过 embeddings 先完成闭环，但后续需要补回 frame 级 embedding。

## 数据与存储约定
- 主库固定为 `PostgreSQL + pgvector`。
- 核心表以 `series`、`episodes`、`ingest_jobs`、`frames` 为主，`shots` 保留兼容。
- `frames` 是默认图片主索引。
- `shots` 不再是当前首轮入库的必经产物。
- 本地文件目录固定为：
  - `data/series/<series_id>/source/`
  - `data/series/<series_id>/audio/`
  - `data/series/<series_id>/frames/`
  - `data/series/<series_id>/artifacts/`

## 检索与接口约定
- `POST /search/image` 是第一优先级主接口。
- 默认检索流程固定为：
  1. 先查 `frame` topK
  2. 结合 `ASR` 文本做轻量排序
  3. 返回 `top1 + top3` 的区间候选
- 第一版返回的主结果必须是时间区间，不是秒级点位。
- 第一版精排至少包含：
  - embedding 相似度
  - ASR 文本重合度
- `POST /search/text` 保留，但优先级低于截图检索。
- 未命中时必须返回显式低置信状态，不能伪造高分结果。

## 开发顺序
1. 先完成 `manifest + schema + ingest_jobs`。
2. 再完成本地 worker，打通 `ASR + frame build`。
3. 然后接入 Gemini frame embedding。
4. 最后实现 `search/image`、`search/text`、评测脚本和演示页。

## 验收标准
- 单集视频能稳定入库并生成可查询的 `frame` 记录。
- 查询结果能返回 `top1` 与 `top3` 区间候选。
- 如仍保留历史 `shot/segment` 数据，仅作兼容与对照，不再作为主架构。
- 整季评测目标：
  - `Top1 命中正确 segment >= 70%`
  - `Top5 命中正确 segment >= 90%`
  - 返回区间覆盖人工标注片段
## 实施规则
- 改动实现前，优先对齐本文件与 [docs/general-plan.md](/home/james/works/projects/drama-finder/docs/general-plan.md)。
- 如出现冲突，以 `docs/general-plan.md` 的最新方案为准，并同步更新本文件。
- 新增设计若会改变技术栈、数据来源、索引层次、主流程或验收标准，必须先更新文档再实现。
- 项目使用 git 管理。
- 每完成一项独立任务或任务板状态从 `IN_PROGRESS` 进入 `DONE`，都应立即提交一次，保持历史可追溯。
