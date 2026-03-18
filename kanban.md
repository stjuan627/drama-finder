# Kanban

最后更新：2026-03-18

## 使用规则
- 开始任何开发前，先看本文件，再看 [AGENTS.md](/home/james/works/projects/drama-finder/AGENTS.md) 和 [docs/general-plan.md](/home/james/works/projects/drama-finder/docs/general-plan.md)。
- 分配 subagent 时，一次只领一个任务，并遵守该任务的 `写入范围`，避免并发冲突。
- 任务状态只允许使用：`TODO`、`IN_PROGRESS`、`BLOCKED`、`DONE`。
- 如果某任务改变了接口、数据结构或默认参数，必须同步更新 `docs/specs/`。
- 每个任务完成后立即提交一次 git commit，提交粒度按任务编号控制。

## 当前项目状态
- 后端骨架已建立：FastAPI、SQLAlchemy、Alembic、RQ worker、Postgres/pgvector、Redis 配置已落地。
- 首个真实分集 `wufulinmen / ep01` 已跑通入库闭环。
- 当前代码主链已切换到：
  - 图片路径：`3s frame`
  - 文本路径：`ASR text`
  - 片头片尾：`manifest` 明配排除区间
- `ASR` 默认后端已切到：`Node.js + sherpa-onnx + Silero VAD`
- 当前成功闭环仍依赖 `INGEST_SKIP_EMBEDDINGS=true`
- 当前主要技术债：
  - 需要把遗留 `scene/segment` 模型与表结构进一步降级为纯兼容层
  - 需要把 `frame embedding` 从阻塞式首轮入库改成后处理
  - 需要完善 `frame + ASR` 方案下的区间评测

## DONE

### K-001 项目骨架初始化
- 状态：`DONE`
- 目标：建立可启动的后端服务基础结构。

### K-002 数据模型与迁移骨架
- 状态：`DONE`
- 目标：落地首批表和迁移骨架。

### K-003 规格文档包
- 状态：`DONE`
- 目标：形成实现级文档包。

### K-004 基础验证
- 状态：`DONE`
- 目标：确认骨架不是死代码。

### K-010 代码质量清理
- 状态：`DONE`
- 目标：清理 lint、导入、worker/queue 基础问题。

### K-011 仓库结构收口
- 状态：`DONE`
- 目标：统一迁移、worker、compose 真值目录。

### K-020 manifest 样例与加载演示
- 状态：`DONE`
- 目标：提供 manifest 示例并覆盖混合扩展名。

### K-021 本地基础设施启动与迁移验证
- 状态：`DONE`
- 目标：打通 Postgres、Redis、Alembic、vector 扩展。

### K-022 首个真实分集入库闭环
- 状态：`DONE`
- 目标：用真实视频与 manifest 完整跑通一集。
- 已验证：
  - `wufulinmen / ep01`
  - 成功任务：`05ca9214-a11e-4f37-b4d6-1391fb82048f`
  - 当前落库：`shots=885 / scenes=885 / frames=3030`
- 说明：
  - 该结果属于过渡闭环结果，不代表最终 `segment-first` 设计已完成

### K-023 方案迁移到 `shot/segment`
- 状态：`DONE`
- 优先级：最高
- 写入范围：`app/models/`、`app/services/ingest.py`、`app/services/retrieval.py`、`docs/`
- 目标：
  - 从当前 `scene/frame` 过渡实现迁移到 `shot/segment` 主体
  - 返回可信区间，而不是秒级点位
- 完成定义：
  - 有明确 `segment` 生成规则
  - 检索主单位改为 `segment`
  - 文档与代码不再强调全库 `1fps frame` 主索引
- 完成记录：
  - 已引入 `Segment` 模型并兼容映射历史 `scenes` 表
  - 入库链路改为 `shot -> representative frames -> segment -> persist`
  - 检索主链改为直接召回 `segment` 并返回 `matched_start_ts / matched_end_ts`
- 备注：
  - 该方案已不再作为当前定稿方向，后续仅保留历史记录

### K-032 主索引切换到 `frame + ASR text`
- 状态：`DONE`
- 优先级：最高
- 写入范围：`app/services/ingest.py`、`app/services/retrieval.py`、`app/schemas/manifest.py`、`docs/`
- 目标：
  - 不再引入 `scene/segment` 作为主检索层
  - 图片路径固定为 `3s` 一截图
  - 文本路径固定为 `ASR` 文本
  - 片头片尾由 manifest 配置，但不改变时间轴
- 完成定义：
  - 图像检索主索引切换到 `frames`
  - 文本检索主路径切换到 `ASR text`
  - manifest 支持 `intro_duration_seconds / outro_duration_seconds`
  - intro/outro 仅影响索引排除范围，不做时间平移

### K-024 片头片尾裁剪
- 状态：`DONE`
- 优先级：高
- 写入范围：`app/services/`、`docs/specs/ingest-pipeline-spec.md`、`docs/specs/defaults.md`
- 目标：
  - 由 manifest 明配 intro/outro 排除区间
  - 返回结果仍保持源视频原始时间轴
- 完成定义：
  - 入库时能基于 manifest 排除 intro/outro 索引
  - 不对命中结果做时间平移

### K-033 ASR 切换到 `SenseVoice Small ONNX`
- 状态：`DONE`
- 优先级：最高
- 写入范围：`app/services/asr.py`、`app/core/`、`pyproject.toml`、`docs/specs/`
- 目标：
  - 用 `SenseVoice Small ONNX` 替换当前 `faster-whisper` 实现层
  - 默认启用量化模型并面向 `CPU`
  - 保持 `ASR` 输出结构为 `[{start, end, text}]`
- 完成定义：
  - 默认模型为 `iic/SenseVoiceSmall`
  - 支持首次自动下载或显式本地模型目录
  - `ingest` 与文本检索下游无需改接口即可继续工作

### K-025 3秒帧索引与代表图规范
- 状态：`DONE`
- 优先级：高
- 写入范围：`app/services/ingest.py`、`docs/specs/schema-spec.md`、`docs/specs/ingest-pipeline-spec.md`
- 目标：
  - 图片主索引固定为 `3s` 一帧
- 完成定义：
  - `frame` 主索引固定为 `3s` 一帧

### K-026 embedding 后处理化
- 状态：`DONE`
- 优先级：高
- 写入范围：`app/services/gemini.py`、`app/services/ingest.py`、`docs/specs/defaults.md`
- 目标：
  - embedding 从阻塞式首轮入库中拆出
  - 只对 `frame` 做主 embedding
  - 文本路径默认不依赖 embedding
- 完成定义：
  - 默认可先入库后补 embedding
  - 成本与耗时显著低于高密度 `1fps frame` 思路

### K-027 检索链路改造成区间返回
- 状态：`DONE`
- 优先级：高
- 写入范围：`app/services/retrieval.py`、`app/api/routes/search.py`、`docs/specs/api-spec.md`、`docs/specs/retrieval-spec.md`
- 目标：
  - 返回 `matched_start_ts / matched_end_ts`
  - 图片走 `frame`，文本走 `ASR`
- 完成定义：
  - 结果是可信区间
  - 不再默认追求秒级落点

### K-028 评测标准改成区间命中
- 状态：`DONE`
- 优先级：中
- 写入范围：`scripts/`、`tests/`、`docs/specs/evaluation-spec.md`
- 目标：
  - 从“秒级误差”改成“区间覆盖命中”
  - 将片头片尾排除区间和 `frame + ASR` 质量纳入评测
- 完成定义：
  - 评测结果更符合当前产品目标

### K-031 Gemini 线上验证
- 状态：`DONE`
- 说明：
  - 已用 `ep02` 验证 `frame embedding`
  - 当前图片向量方案定稿为“纯图片 embedding”
  - `ep02` 纯图片 embedding 评测结果：
    - `Top1 = 72.22%`
    - `Top5 = 88.89%`

## TODO

### K-034 文本检索轻量增强
- 状态：`DONE`
- 优先级：高
- 写入范围：`app/services/retrieval.py`、`app/db/`、`migrations/`、`tests/`、`docs/specs/retrieval-spec.md`
- 目标：
  - 不改技术栈前提下提升文本检索对错别字、近音字、ASR 噪声的鲁棒性
  - 不引入 Elasticsearch / Solr / OpenSearch
  - 不为文本路径引入 embedding
- 完成定义：
  - 引入等价 trigram 轻量模糊召回能力
  - 查询文本有统一归一化
  - 支持 `shot` 邻接文本拼接召回
  - 文本检索评测指标相较当前基线有可见提升

### K-035 embedding 回填队列化
- 状态：`TODO`
- 优先级：低
- 写入范围：`app/services/ingest.py`、`app/workers/`、`app/api/routes/`、`docs/specs/`
- 目标：
  - 将 `frame embedding` 回填从手动入口改成正式队列任务
  - 支持任务进度、恢复和重试
- 完成定义：
  - 可以按 `episode` 提交独立 backfill job
  - worker 可恢复未完成帧
  - API 或脚本可查询回填状态

### K-029 演示页面
- 状态：`TODO`
- 优先级：中
- 写入范围：前端目录或后续新增 UI 目录
- 目标：
  - 提供最小页面：任务提交、任务状态、截图上传、区间结果展示
- 完成定义：
  - 非技术用户可以完成一次片段区间定位演示

## 推荐的下一个开发顺序
1. 重试补齐 `ep02` 剩余失败的 `frame embedding`
2. 视演示需要推进 `K-029`
3. 低优先级再做 `K-035`
