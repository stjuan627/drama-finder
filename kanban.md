# Kanban

最后更新：2026-03-17

## 使用规则
- 开始任何开发前，先看本文件，再看 [AGENTS.md](/home/james/works/projects/drama-finder/AGENTS.md) 和 [docs/general-plan.md](/home/james/works/projects/drama-finder/docs/general-plan.md)。
- 分配 subagent 时，一次只领一个任务，并遵守该任务的 `写入范围`，避免并发冲突。
- 任务状态只允许使用：`TODO`、`IN_PROGRESS`、`BLOCKED`、`DONE`。
- 如果某任务改变了接口、数据结构或默认参数，必须同步更新 `docs/specs/`。
- 每个任务完成后立即提交一次 git commit，提交粒度按任务编号控制。

## 当前项目状态
- 后端骨架已建立：FastAPI、SQLAlchemy、Alembic、RQ worker、Postgres/pgvector、Redis 配置已落地。
- 核心规格文档已落地：`docs/specs/` 已覆盖 manifest、schema、pipeline、job、retrieval、API、evaluation、defaults、repo structure。
- 基础验证已通过：
  - `.venv/bin/pytest -q` 通过，当前 `2 passed`
  - FastAPI `/healthz` smoke test 返回 `200`
- 当前主要技术债：
  - 首个真实剧集入库仍在推进中，`K-022` 尚未完成
  - 仓库仍有少量旧残留目录和缓存目录，需要继续收口
  - Gemini scene merge 与 embedding 还没进入真实线上调用阶段
  - 当前真实入库先按 `faster-whisper small` 验证链路，不以最终 ASR 精度为准

## DONE

### K-001 项目骨架初始化
- 状态：`DONE`
- 目标：建立可启动的后端服务基础结构。
- 写入范围：`app/`、`scripts/`、`pyproject.toml`、`.env.example`、`README.md`
- 完成定义：
  - FastAPI 应用存在
  - 数据库 session 存在
  - worker 入口存在
  - 依赖可安装

### K-002 数据模型与迁移骨架
- 状态：`DONE`
- 目标：落地 `series / episodes / ingest_jobs / shots / scenes / frames`
- 写入范围：`app/models/`、`migrations/`、`alembic.ini`
- 完成定义：
  - ORM 模型存在
  - 初始迁移存在
  - pgvector 列已建模

### K-003 规格文档包
- 状态：`DONE`
- 目标：将方案细化为实现级文档。
- 写入范围：`docs/specs/`
- 完成定义：
  - `manifest-spec.md`
  - `schema-spec.md`
  - `ingest-pipeline-spec.md`
  - `job-lifecycle-spec.md`
  - `retrieval-spec.md`
  - `api-spec.md`
  - `evaluation-spec.md`
  - `defaults.md`
  - `repo-structure.md`

### K-004 基础验证
- 状态：`DONE`
- 目标：确认骨架不是死代码。
- 写入范围：无
- 完成定义：
  - `pytest` 通过
  - `app.main` 可导入
  - `/healthz` 返回 `200`

### K-010 代码质量清理
- 状态：`DONE`
- 优先级：高
- 写入范围：`app/api/routes/`、`app/models/`、`app/services/`、`migrations/`、`scripts/`
- 依赖：K-001、K-002
- 完成定义：
  - `.venv/bin/ruff check app tests scripts migrations` 通过

### K-020 manifest 样例与加载演示
- 状态：`DONE`
- 优先级：高
- 写入范围：`manifests/`、`docs/specs/manifest-spec.md`、`tests/`
- 依赖：K-003
- 完成定义：
  - 样例 manifest 可通过校验
  - manifest 示例与文档完全一致
  - 覆盖 `01.mp4 / 04.mkv` 混合扩展名

## IN_PROGRESS

### K-011 仓库结构收口
- 状态：`DONE`
- 优先级：高
- 写入范围：仓库根目录、`workers/`、`migrations/`、`alembic/`
- 依赖：K-001、K-002
- 已解决项：
  - 仅保留 `migrations/` 作为迁移真值
  - 仅保留 `compose.yaml` 作为容器真值
  - 仅保留 `app/workers/` 作为 worker 真值
- 完成定义：
  - 基础设施目录只保留一套真值
  - 运行入口与文档引用一致
  - 无多余历史骨架混淆当前实现

### K-021 本地基础设施启动与迁移验证
- 状态：`DONE`
- 优先级：高
- 写入范围：`compose.yaml` 或统一后的容器文件、`README.md`
- 依赖：K-010、K-011
- 完成定义：
  - 数据库可创建表
  - Redis 队列可连接
  - README 有最小启动命令

## TODO

### K-022 入库任务端到端跑通一集
- 状态：`IN_PROGRESS`
- 优先级：最高
- 写入范围：`app/services/ingest.py`、`app/services/media.py`、`app/services/asr.py`、`app/services/scene_detection.py`、`app/workers/`
- 依赖：K-020、K-021
- 目标：
  - 用真实本地视频和 manifest 完整跑一集
  - 产出音轨、ASR、shots、frames、scenes、数据库记录
- 完成定义：
  - `POST /ingest/episode` 可提交任务
  - worker 能处理到 `completed`
  - `data/series/<series_id>/<episode_id>/` 下产物完整

### K-023 Scene 合并与 Gemini 接入实测
- 状态：`TODO`
- 优先级：高
- 写入范围：`app/services/gemini.py`、`app/services/ingest.py`
- 依赖：K-022
- 目标：
  - 用 `gemini-3-flash-preview` 验证 scene merge 输出格式
  - 用 `gemini-embedding-2-preview` 验证 scene/frame embedding
- 完成定义：
  - API key 配置后能生成合法结果
  - 异常回退和日志可用

### K-024 检索链路端到端验证
- 状态：`TODO`
- 优先级：高
- 写入范围：`app/services/retrieval.py`、`app/api/routes/search.py`、`tests/`
- 依赖：K-022、K-023
- 目标：
  - 对已入库剧集执行截图检索与文本检索
  - 返回 `top1 + top3`
- 完成定义：
  - `/search/image` 能返回结构化结果
  - `/search/text` 能返回结构化结果
  - 低置信命中处理正确

### K-025 评测脚本与基线实现
- 状态：`TODO`
- 优先级：中
- 写入范围：`scripts/`、`tests/`、`docs/specs/evaluation-spec.md`
- 依赖：K-024
- 目标：
  - 实现纯 `1fps frame` 基线
  - 实现主方案与基线对比脚本
- 完成定义：
  - 输出统一评测结果格式
  - 可比较 `Top1 / Top5 / 时间误差 / embedding 数量 / 处理时长`

### K-026 演示页面
- 状态：`TODO`
- 优先级：中
- 写入范围：前端目录或后续新增 UI 目录
- 依赖：K-024
- 目标：
  - 提供最小页面：任务提交、任务状态、截图上传、结果展示
- 完成定义：
  - 非技术用户可以完成一次截图定位演示

## BLOCKED

### K-030 真实数据验证
- 状态：`IN_PROGRESS`
- 当前输入：
  - `data/series/wufulinmen/manifest.yml`
  - `data/series/wufulinmen/01.mp4` 到 `05.mp4`
- 当前进展：
  - `ep01` 已成功进入真实入库执行

### K-031 Gemini 线上验证
- 状态：`TODO`
- 阻塞项：
  - 需要至少一集真实可入库数据
- 解锁条件：
  - `K-022` 完成或有一集可用于手工验证的数据

## 推荐的 subagent 切分
- Subagent A：K-010 代码质量清理
  - 写入范围：`app/api/routes/`、`app/models/`、`app/services/`、`migrations/`、`scripts/`
- Subagent B：K-011 仓库结构收口
  - 写入范围：仓库根目录、`workers/`、`migrations/`、容器与启动文件
- Subagent C：K-020 manifest 样例与校验补强
  - 写入范围：`manifests/`、`tests/`、`docs/specs/manifest-spec.md`
- 主线程：K-021/K-022
  - 原因：这两项最依赖上下文和真实运行结果，不适合一开始就外包

## 下一步顺序
1. 先完成 K-010，清掉 lint 和明显实现噪音。
2. 再完成 K-011，统一仓库结构和运行真值。
3. 然后做 K-020 + K-021，补 manifest 样例并启动本地基础设施。
4. 最后进入 K-022，用真实视频跑第一集端到端。
