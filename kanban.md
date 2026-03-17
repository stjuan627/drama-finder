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
- 首个真实分集 `wufulinmen / ep01` 已跑通入库闭环。
- 当前代码仍处于过渡期：
  - 已能生成 `shots/scenes/frames`
  - 但目标设计应迁移到 `shot/segment` 主体
  - 当前成功闭环依赖 `INGEST_SKIP_EMBEDDINGS=true`
- 当前主要技术债：
  - 需要把 `scene/frame` 过渡实现升级为 `segment-first`
  - 需要引入片头片尾裁剪
  - 需要取消全库 `1fps` 主索引思路
  - 需要把 embedding 生成从阻塞式入库改成 segment 级后处理
  - 已确认 shot 质检可接受，后续应围绕 `first/mid` 双图继续收敛

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

## IN_PROGRESS

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

### K-024 片头片尾裁剪
- 状态：`IN_PROGRESS`
- 优先级：高
- 写入范围：`app/services/`、`docs/specs/ingest-pipeline-spec.md`、`docs/specs/defaults.md`
- 目标：
  - 基于本地跨集重复片段检测裁掉片头片尾
  - 必要时支持 Gemini 复核
- 完成定义：
  - 入库前能识别并剔除 intro/outro 区间
  - 对检索库不再写入明显重复的片头片尾内容

## TODO

### K-025 segment 构建与代表图规范
- 状态：`TODO`
- 优先级：高
- 写入范围：`app/services/ingest.py`、`docs/specs/schema-spec.md`、`docs/specs/ingest-pipeline-spec.md`
- 目标：
  - 每个 shot 默认保存 `first/mid` 代表图
  - 多个连续 shot 合并为 `5s - 15s` 的 segment
- 完成定义：
  - 代表图和时间区间可用于人工质检
  - `segment` 生成不再等同于 `1 shot = 1 scene`

### K-026 embedding 后处理化
- 状态：`TODO`
- 优先级：高
- 写入范围：`app/services/gemini.py`、`app/services/ingest.py`、`docs/specs/defaults.md`
- 目标：
  - embedding 从阻塞式首轮入库中拆出
  - 只对 `segment` 做主 embedding
  - `shot/frame` embedding 作为可选局部增强
- 完成定义：
  - 默认可先入库后补 embedding
  - 成本与耗时显著低于当前全量 `frame` 思路

### K-027 检索链路改造成区间返回
- 状态：`TODO`
- 优先级：高
- 写入范围：`app/services/retrieval.py`、`app/api/routes/search.py`、`docs/specs/api-spec.md`、`docs/specs/retrieval-spec.md`
- 目标：
  - 返回 `matched_start_ts / matched_end_ts`
  - 以 `segment` 为主召回
- 完成定义：
  - 结果是可信区间
  - 不再默认追求秒级落点

### K-028 评测标准改成区间命中
- 状态：`TODO`
- 优先级：中
- 写入范围：`scripts/`、`tests/`、`docs/specs/evaluation-spec.md`
- 目标：
  - 从“秒级误差”改成“区间覆盖命中”
  - 将片头片尾裁剪和 segment 质量纳入评测
- 完成定义：
  - 评测结果更符合当前产品目标

### K-029 演示页面
- 状态：`TODO`
- 优先级：中
- 写入范围：前端目录或后续新增 UI 目录
- 目标：
  - 提供最小页面：任务提交、任务状态、截图上传、区间结果展示
- 完成定义：
  - 非技术用户可以完成一次片段区间定位演示

## BLOCKED

### K-031 Gemini 线上验证
- 状态：`TODO`
- 说明：
  - 真实 API key 已可用
  - 当前已完成 scene merge 的线上验证
  - 但正式的 segment embedding 成本与策略还未固化

## 推荐的下一个开发顺序
1. 完成 `K-023`，把方案正式迁移到 `shot/segment`
2. 完成 `K-024`，把片头片尾从检索库里剔除
3. 完成 `K-025`，落实代表图和 segment 合并
4. 完成 `K-026`，把 embedding 变成 segment 级后处理
5. 完成 `K-027/K-028`，再做检索与评测
