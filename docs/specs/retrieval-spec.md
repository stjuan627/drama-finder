# 检索规格

## 查询类型
- `POST /search/image`
- `POST /search/text`

## 主检索单位
- 图片主单位是 `frame`
- 文本主单位是 `ASR` 文本命中的时间区间
- `shot` 只负责底层切分

## 图像检索
- 查询流程：
  1. 上传图片生成 query embedding
  2. 查询 `Frame.embedding` 取 `image_search_top_k`
  3. 直接返回 `frame_ts ~ frame_ts+3s` 的区间候选
- 可用性约定：
  - `raw_metadata.index_excluded=true` 的帧不得参与返回
  - 未配置 Gemini 或尚未补齐 `frame embedding` 时，返回 `low_confidence=true` 与空结果，不伪造高分命中
- 返回结果应以 `matched_start_ts / matched_end_ts` 为主

## 文本检索
- 查询流程：
  1. 对查询文本做归一化
  2. 对 `shot.raw_metadata.asr_text` 与邻接 `shot` 拼接文本做轻量召回
  3. 评分至少包含：
     - 子串命中
     - ngram overlap
     - trigram 相似度（`pg_trgm` 或等价实现）
  4. 返回最相关的 `shot` 或文本片段区间
  5. 不引入 `scene/segment` 中间层
  6. 当前不再返回 `shot` 代表图证据
  7. 返回前对同集相邻命中区间做合并，避免展示多个近似重复候选
- 约束：
  - 第一阶段不引入 Elasticsearch / Solr / OpenSearch
  - 第一阶段不为文本路径引入 embedding
  - 目标是先用轻量方案提升错别字和 ASR 噪声下的召回率

## 返回结构
- `series_id`
- `episode_id`
- `matched_start_ts`
- `matched_end_ts`
- `score`
- `evidence_images[]`
- `evidence_text[]`

## 低置信规则
- `low_confidence = true` 时，表示候选存在但可信度不足。

## 当前实现边界
- 当前实现按 `frame + ASR text` 双路径返回区间。
- `segments/scenes` 如仍存在，只保留为历史兼容结构。
