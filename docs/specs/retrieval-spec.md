# 检索规格

## 查询类型
- `POST /search/image`
- `POST /search/text`

## 图像检索
- 查询流程：
  1. 上传图片先生成 query embedding
  2. 查询 `Scene.embedding` 取 `scene_top_k`
  3. 在每个候选 scene 内查询 `Frame.embedding` 取 `frame_top_k`
  4. 取候选帧第一名作为该 scene 的定位结果
  5. 使用轻量 `_rank()` 规则分数做最终排序
- `matched=true` 条件：
  - 至少存在命中
  - top1 `score >= LOW_CONFIDENCE_THRESHOLD`

## 文本检索
- 查询流程：
  1. 文本生成 query embedding
  2. 查询 `Scene.embedding` 取 `scene_top_k`
  3. 直接按 scene 返回结果
- `matched_ts` 固定取 `scene.start_ts`。

## 返回结构
- `series_id`
- `episode_id`
- `matched_ts`
- `scene_start_ts`
- `scene_end_ts`
- `score`
- `scene_summary`
- `evidence_frames[]`
- `evidence_text[]`

## 低置信规则
- `SearchImageResponse.low_confidence = true` 时，表示候选存在但可信度不足。

## 当前实现边界
- `_rank()` 当前仍是启发式规则，不是学习排序器。
- 当前实现依赖 Gemini embedding，可离线入库，但在线查询前必须配置 `GEMINI_API_KEY`。
