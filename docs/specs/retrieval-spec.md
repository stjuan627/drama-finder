# 检索规格

## 查询类型
- `POST /search/image`
- `POST /search/text`

## 主检索单位
- 主单位是 `segment`
- `shot` 只负责底层切分与辅助质检
- 全库不默认查询 `frame`
- `shot` 的默认视觉表示为 `first/mid` 两张图

## 图像检索
- 查询流程：
  1. 上传图片生成 query embedding
  2. 查询 `Segment.embedding` 取 `segment_top_k`
  3. 对候选 `segment` 做轻量精排
  4. 返回可信区间
- 返回结果应以 `matched_start_ts / matched_end_ts` 为主

## 文本检索
- 查询流程：
  1. 文本生成 query embedding
  2. 查询 `Segment.embedding` 取 `segment_top_k`
  3. 直接按 `segment` 返回结果

## 返回结构
- `series_id`
- `episode_id`
- `matched_start_ts`
- `matched_end_ts`
- `score`
- `segment_summary`
- `evidence_images[]`
- `evidence_text[]`

## 低置信规则
- `low_confidence = true` 时，表示候选存在但可信度不足。

## 当前实现边界
- 当前代码仍保留 `scene/frame` 过渡结构。
- 正式检索应迁移到 `segment` 主体，不再依赖全库 `1fps frame` 候选扫描。
