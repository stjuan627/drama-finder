# 入库 API 与 Pipeline 关系

## 说明
- 本文件仅做流程索引。
- 真实接口字段以 [api-spec.md](/home/james/works/projects/drama-finder/docs/specs/api-spec.md) 为准。
- 真实 pipeline 阶段以 [ingest-pipeline-spec.md](/home/james/works/projects/drama-finder/docs/specs/ingest-pipeline-spec.md) 为准。

## 流程
1. API 收到 `series_id + episode_id`
2. manifest 同步到 `series/episodes`
3. 创建 `ingest_jobs`
4. RQ 入队
5. worker 执行 pipeline
6. 写入 `shots/frames`
7. 查询接口分别消费 `frame` 与 `ASR` 文本结果
