# 评测规格

## 评测目标
- 比较主方案与纯 `1fps frame` 基线。
- 评估：
  - 正确 scene 命中率
  - 时间定位误差
  - 数据处理成本

## 数据集
- 单位：截图样本
- 每条样本至少包含：
  - `series_id`
  - `episode_id`
  - `image_path`
  - `gt_ts`
  - `gt_scene_start_ts`
  - `gt_scene_end_ts`

## 指标定义
- `Top1 命中正确 scene`
  - top1 返回的 `matched_ts` 落入人工标注 scene 窗口
- `Top5 命中正确 scene`
  - top5 任一命中满足上述条件
- `时间误差中位数`
  - `abs(predicted_ts - gt_ts)` 的中位数
- `每集 embedding 数量`
  - scene 记录实际写入 embedding 的数量
- `单集处理时长`
  - 从任务 `started_at` 到 `finished_at`

## 验收线
- `Top1 命中正确 scene >= 70%`
- `Top5 命中正确 scene >= 90%`
- `时间误差中位数 <= 5 秒`

## 输出格式
- 每次评测至少输出：
  - 数据集规模
  - 指标表
  - 失败样本列表
  - 处理时长汇总

