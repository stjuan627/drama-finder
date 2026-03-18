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
  1. 文本与 `ASR` 文本做匹配
  2. 返回最相关的 `shot` 或文本片段区间
  3. 不引入 `scene/segment` 中间层
  4. 当前不再返回 `shot` 代表图证据

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
