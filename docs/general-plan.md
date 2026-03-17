# 开发准备与模块拆分计划

## 摘要
- 当前方案已经足够进入开发准备，但不建议直接无拆分开工。
- 第一阶段按 `Python + FastAPI + PostgreSQL + pgvector + Redis/RQ` 固定技术栈推进。
- 入库采用 `API 提交任务 + 本地后台 worker 离线处理`，媒体文件与中间产物全部落在本地文件系统。
- 剧集基础元数据不从文件名猜测，统一由 `manifest` 提供；文件命名约定只作为辅助校验，不作为唯一事实源。

## 模块拆分
1. 项目骨架模块
- 建立 `FastAPI + SQLAlchemy + Alembic + RQ worker` 的基础工程。
- 配置 `Postgres`、`pgvector`、`Redis`、本地 `data/` 目录和 Gemini API 配置。
- 提供健康检查、配置加载、日志和任务状态查询基础能力。

2. 剧集清单与元数据模块
- 为每部剧定义一个 `manifest.yaml` 或 `manifest.json`。
- manifest 固定字段为：`series_id`、`series_title`、`season_label`、`language`、`video_root`、`episodes[]`。
- `episodes[]` 每项固定字段为：`episode_id`、`episode_no`、`title`、`filename`。
- 入库前先校验 manifest 与本地视频文件是否匹配；缺文件、重名、重复 episode_no 直接报错。

3. 入库任务模块
- `POST /ingest/episode` 接收 `series_id + episode_id`，不直接上传大文件。
- Worker 按固定阶段执行：`加载 manifest -> 定位视频 -> ffmpeg 抽音轨 -> ASR -> PySceneDetect -> 1fps 抽帧 -> 代表帧选择 -> scene 合并 -> embedding 生成 -> 写库`。
- 每个阶段写入任务状态与计数；失败时保留已完成产物，不回滚媒体文件。
- 重试策略固定为“按 episode 级幂等覆盖”，同一 `series_id + episode_id` 重跑时替换旧索引和旧元数据。

4. 数据模型与存储模块
- 表结构固定为：`series`、`episodes`、`ingest_jobs`、`shots`、`scenes`、`frames`。
- `scenes` 保存 `start_ts`、`end_ts`、`summary`、`asr_text`、`embedding`。
- `frames` 保存 `frame_ts`、`image_path`、`context_asr_text`、`embedding`。
- `shots` 作为中间结构入库，保留边界与代表帧引用，供评测和问题排查。
- 本地文件结构固定为：`data/series/<series_id>/source/`、`data/series/<series_id>/audio/`、`data/series/<series_id>/frames/`、`data/series/<series_id>/artifacts/`。

5. scene 合并与 embedding 模块
- shot 边界先由 `PySceneDetect` 生成。
- scene 合并由 `Gemini 3 Flash` 基于相邻 shot 的代表帧和对应 ASR 文本完成。
- scene embedding 输入固定为：`代表帧图像 + scene_summary + scene 时间窗 ASR 文本`。
- frame embedding 输入固定为：`当前帧图像 + 当前时间点前后 5 秒 ASR 文本`。
- 第一版不引入 OCR，不处理画面文字检索。

6. 查询服务模块
- `POST /search/image` 先查 `scene` topK，再在候选 scene 时间窗内查 `frame` topK。
- 精排分数固定由三部分组成：`scene/frame embedding 相似度`、`ASR 文本重合度`、`邻近帧连续性`。
- 返回结构固定为：`series_id`、`episode_id`、`matched_ts`、`scene_start_ts`、`scene_end_ts`、`score`、`scene_summary`、`evidence_frames`、`evidence_text`。
- `POST /search/text` 保留为辅助接口，采用 `BM25 + text embedding` 混合召回 scene，再回落到 frame。

7. 评测与基线模块
- 保留一个纯基线：`仅 1fps frame 检索`。
- 主方案与基线共用同一评测集和同一结果格式。
- 评测指标固定为：`Top1 命中正确 scene`、`Top5 命中正确 scene`、`Top1 时间误差中位数`、`每集 embedding 数量`、`单集处理时长`。

## 需要补齐的实现级规格
- `manifest` 文件格式文档。
- 数据库 schema 文档与迁移草案。
- 入库任务状态机文档，至少包含 `queued`、`running`、`failed`、`completed`。
- API 契约文档，明确请求字段、响应字段、错误码与未命中返回。
- 检索默认参数文档，固定 `scene topK`、`frame topK`、`ASR context window`、精排权重默认值。

## 开发顺序
1. 先完成 `manifest + schema + ingest_jobs` 三件套，因为这是后续所有模块的基础接口。
2. 再完成本地入库 worker，先打通 `ASR + shot detection + 1fps frame extraction`，暂时允许 scene 合并先用简单规则占位。
3. 然后接入 `Gemini 3 Flash scene 合并` 与 `gemini-embedding-2-preview`，完成 scene/frame 双层索引。
4. 最后实现 `search/image`、`search/text`、评测脚本和演示页。

## 测试与验收
- manifest 校验必须覆盖缺文件、重复集号、非法路径、重复 series_id。
- 单集入库必须能生成可查询的 `scene` 和 `frame` 记录，并且任务状态正确落库。
- 截图查询必须返回 top1 与 top3 候选；未命中时返回显式低置信状态。
- 在整季评测集上达到：`Top1 命中正确 scene >= 70%`、`Top5 >= 90%`、`时间误差中位数 <= 5 秒`。
- 基线与主方案必须能同场评测，输出统一格式结果。

## 假设与默认项
- 默认只处理中文剧集。
- 默认输入是本地视频目录，不支持远程拉取。
- 默认媒体与产物都落在本地磁盘，不接对象存储。
- 默认本地 ASR 使用 `faster-whisper` 作为首选实现。
- 默认后台队列使用 `Redis + RQ`，不额外引入更重的工作流系统。
- 默认第一阶段先完成后端闭环，再补最小演示页面。
