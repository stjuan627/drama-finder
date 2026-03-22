# Google Embedding Batch 调研与接入建议

## 目标
- 评估 Google 的向量化能力是否支持 batch 路径来降低 embedding 成本。
- 评估该能力如何和当前仓库的离线入库设计结合。
- 给后续实现提供保守、可落地的接入方案。

## 调研结论

### 1. 可以做 batch，但要区分三种完全不同的“批量”
- `单请求内数组输入`：一次同步请求里提交多条内容，主要减少网络往返和客户端开销。
- `异步 Batch API / Batch Prediction`：提交离线任务，平台异步处理并产出结果。
- `本地线程并发`：客户端同时发起多次在线请求，只是提高吞吐。

只有第二类真正的异步 batch，才可能对应明显的计费优惠。第一类和第三类不能按“成本减半”理解。

### 2. “可节省 50% 成本”不是无条件成立
- 外部调研显示，Google 在部分 Gemini / Vertex 的 batch 路径上存在相对在线调用更低的计费方式。
- 但这个结论只在以下前提同时成立时才有效：
  - 使用的是 Google 官方明确支持折扣的 batch 产品；
  - 该 batch 产品支持当前实际使用的 embedding 模型与模态；
  - 官方定价页对该模型/产品/区域明确写了折扣，而不是只支持 batch 执行能力。

因此，当前只能得出“存在可达 50% 左右降本的可能路径”，不能直接写成“项目接上后必然节省 50%”。

### 3. 当前项目最应该先做的是拆执行层，而不是立刻改 Google 调用方式
- 当前仓库已经有 `deferred` 的 embedding 语义。
- 但实际执行仍然绑在本地 backfill 方法里，和真正的外部异步 batch 作业模型并不匹配。
- 所以最稳的演进顺序是：
  1. 先把 embedding 执行从 ingest 主流程中解耦；
  2. 再抽象出统一 embedding backend；
  3. 最后把 batch 作为可选后端接入。

## 当前仓库现状

### 1. 主入库流程只登记 deferred，不真正生成 embedding
- `app/services/ingest.py` 中的 `IngestPipeline.run()` 会在落库时生成 `Frame` 记录，并把 `embedding` 置为 `None`。
- 同时在 `raw_metadata.embedding_status` 中记录 `pending_backfill`。
- `job.artifacts` 也会记录 `embedding_mode = deferred` 和 `pending_frame_embeddings`。

这说明当前设计方向本身是对的：主入库先完成，embedding 允许后补。

### 2. 当前 backfill 不是独立任务，而是同步方法
- `app/services/ingest.py` 中的 `backfill_frame_embeddings()` 负责补 embedding。
- 它通过 `ThreadPoolExecutor` 并发执行 `_embed_frame_payload()`。
- 这属于“本地线程并发逐条在线调用”，不属于 Google 的 batch 产品。

### 3. 当前 Gemini 服务只有单次在线调用接口
- `app/services/gemini.py` 当前只有 `client.models.embed_content(...)`。
- `embed_text()`、`embed_image()`、`embed_multimodal()` 都是同步单次调用模式。
- `embed_frame_document()` 当前实际只调用 `embed_image()`，没有使用 `context_text`。

这意味着当前 frame embedding 事实上是图片向量，不是图片 + 文本联合向量。

### 4. 当前 RQ 队列只处理 ingest
- `app/workers/tasks.py` 当前只有 `run_ingest_job()`。
- `app/services/queue.py` 当前只有 `enqueue_ingest()`。

也就是说，现在还没有独立的 embedding worker 或 embedding job。

## 对现有设计的影响判断

### 1. 直接把 batch 逻辑塞进现有 ingest 线程池不是好方案
原因有三点：
- 真正的 batch 是外部异步任务，不适合嵌在当前同步 backfill 循环里等待；
- batch 任务通常有更长延迟，不应阻塞主 ingest 生命周期；
- batch 回写常见为部分成功、部分失败，需要单独的状态管理和幂等处理。

### 2. 最佳落点是保留 deferred 语义，新增独立 embedding 队列
建议保持现有业务语义不变：
- ingest 完成后，frame 仍先以 `pending_backfill` 状态入库；
- 后续由独立 embedding job 处理待回填记录；
- 在线调用和 batch 调用都挂在这个 job 的执行层下。

这样有两个好处：
- 不需要改主入库契约；
- 后续可以在不动 ingest 主流程的前提下，切换不同 embedding 后端。

## 推荐接入方案

### Phase 1：先做独立 embedding job
目标是先把执行形态改对。

建议改动：
- 在 `app/workers/tasks.py` 新增独立任务，例如 `run_embedding_backfill_job()`。
- 在 `app/services/queue.py` 新增入队方法，例如 `enqueue_embedding_backfill()`。
- 将 `backfill_frame_embeddings()` 从“本地同步辅助方法”提升为“embedding worker 的核心执行逻辑”。
- 让 ingest 完成后只负责登记待处理数量，是否自动触发 embedding job 可以单独配置。

这一阶段继续使用现有在线 `embed_content(...)` 即可，不急着切 batch。

### Phase 2：抽象统一 embedding backend
建议引入一个清晰的 provider 抽象，至少区分：
- `online provider`：继续走现有同步接口；
- `batch provider`：提交异步 batch 任务，等待完成后回写。

统一抽象后，worker 不再关心底层是在线逐条调用还是离线 batch。

### Phase 3：把 batch 作为可选后端接入
只有在下列条件确认后，才建议真正启用 batch：
- 官方文档明确支持当前实际使用的 embedding 模型和模态；
- 官方定价明确说明该路径有折扣；
- 当前 backlog 足够大，且允许更高延迟；
- 可以接受 batch 结果的异步回写语义。

如果这些条件不同时满足，就继续用独立队列 + 在线并发，收益更确定。

## 数据与状态建议

### 1. 每条 embedding 结果至少记录以下元数据
- `provider`
- `model`
- `model_version`
- `job_id` 或 `batch_id`
- `status`
- `source_revision`
- `updated_at`

目的：保证 episode 重跑、批量重试、模型切换时可以追溯并防止脏写。

### 2. 必须做源版本校验
如果某一集在 batch 运行期间已经被重新 ingest：
- 旧 batch 结果不应直接写回当前索引；
- 应丢弃旧结果，或者写入隔离版本后再决定是否切换。

否则会把过期向量写回新一轮数据，破坏幂等覆盖语义。

### 3. 需要 item 级失败状态
真正的 batch 常见问题不是整单失败，而是：
- 少量 item 失败；
- 个别结果缺失；
- 返回格式异常；
- 任务成功但部分记录未产出 embedding。

因此回写逻辑不能只看 job 级状态，必须保留 item 级状态与重试能力。

## 当前最关键的不确定项

### 1. 当前 frame embedding 实际是图片向量
`embed_frame_document()` 没有使用 `context_text`，所以当前主路径本质上是 image embedding。

这意味着后续核实 batch 能力时，重点不是“text embedding 能不能 batch”，而是：
- 当前目标 batch 路径是否支持图片 embedding；
- 输出向量空间是否与当前模型一致；
- 切换后是否需要全量重建索引。

### 2. 新旧模型不能混写到同一索引
如果 batch 路径要求更换模型、维度或向量空间：
- 不能把新旧 embedding 混存后直接检索；
- 需要按 episode 或全库进行重建。

## 推荐决策

### 建议现在就做
- 新增独立 embedding 队列与 worker 任务。
- 抽象在线 / batch 两类 embedding backend。
- 补足 embedding 元数据、状态机和源版本校验。

### 建议暂时不要直接做
- 不要把“本地线程并发”误当作 Google batch。
- 不要在未核实模型、模态和官方定价前，就承诺 50% 降本。
- 不要把真正的异步 batch 直接塞回 `IngestPipeline.run()` 生命周期。

## 一句话结论
- Google 的 embedding 大概率存在可用于降本的 batch 路径，但要以官方支持的模型、模态和计费为准。
- 对当前仓库来说，最稳的结合方式不是直接改现有线程池，而是保留 `deferred backfill` 语义，先新增独立 embedding 队列，再把 batch 作为可选执行后端接入。
