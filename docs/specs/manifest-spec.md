# Manifest 规格

## 目的
- `manifest` 是剧集基础元数据唯一事实源。
- 入库任务只能通过 `series_id` 反查 manifest，不能通过文件名猜剧名。

## 文件位置
- 根目录：`APP_MANIFEST_ROOT`
- 命名规则：
  - `<series_id>.yaml`
  - `<series_id>.yml`
  - `<series_id>.json`
- 查找顺序固定为：`.yaml` -> `.yml` -> `.json`
- 仓库内提供参考示例：[manifests/example-series.yaml](/home/james/works/projects/drama-finder/manifests/example-series.yaml)

## 顶层结构
- `version: string`
  - 必填
  - 当前仅允许 `v1`
- `series_id: string`
  - 必填
  - 长度 `1..128`
  - 仅允许作为系统逻辑标识，不允许依赖中文标题生成
- `series_title: string`
  - 必填
  - 长度 `1..255`
- `season_label: string | null`
  - 选填
  - 最大长度 `128`
- `language: string`
  - 必填
  - 默认 `zh-CN`
  - 最大长度 `32`
- `video_root: string`
  - 必填
  - 相对路径
  - 相对于 manifest 所在目录解析
- `episodes: Episode[]`
  - 必填
  - 最少 `1` 项

## Episode 结构
- `episode_id: string`
  - 必填
  - 长度 `1..128`
  - 在同一 `series_id` 内唯一
- `episode_no: int`
  - 必填
  - `>= 1`
  - 在同一 `series_id` 内唯一
- `title: string`
  - 必填
  - 长度 `1..255`
- `filename: string`
  - 必填
  - 相对路径
  - 不允许绝对路径
  - 允许不同扩展名混用，例如 `01.mp4`、`04.mkv`

## 校验规则
- manifest 版本不为 `v1` 时直接拒绝。
- `filename` 是绝对路径时直接拒绝。
- `episode_id` 重复时直接拒绝。
- `episode_no` 重复时直接拒绝。
- `video_root/filename` 解析后的文件不存在时直接拒绝。
- `video_root` 不允许逃逸 manifest 目录之外的非法相对路径。
- 扩展名不要求统一；只要底层 `ffmpeg/ffprobe` 能正常读取即可。

## 示例约定
- 推荐在 `manifest` 中直接保留真实原始文件名，不要求先统一容器格式。
- 以下混合扩展名是合法示例：
  - `01.mp4`
  - `02.mp4`
  - `03.mp4`
  - `04.mkv`
- 只要 `video_root` 下文件存在，`ManifestService` 必须允许此类混合输入通过校验。

## 入库同步规则
- `series` 表以 `series_id` 为唯一键。
- `episodes` 表以 `(series_pk, episode_id)` 为唯一键。
- manifest 中存在的集目必须同步到数据库。
- 已存在记录允许被 manifest 覆盖更新：`title`、`episode_no`、`source_path`、`source_filename`。
- manifest 删除某集时，本期实现不自动删库；该行为由人工控制。
- 第一版不要求在入库前手动把 `mkv` 全部转成 `mp4`。
