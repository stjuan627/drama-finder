# 仓库结构规范

## 主结构
- `app/`
  - `api/` HTTP 路由
  - `core/` 配置与默认值
  - `db/` engine、session
  - `models/` ORM 模型
  - `schemas/` Pydantic 输入输出
  - `services/` manifest、pipeline、检索、Gemini、队列
  - `workers/` RQ worker 与任务入口
- `migrations/`
  - Alembic 迁移目录
- `docs/specs/`
  - 实现级规格文档
- `tests/`
  - 单元测试
- `scripts/`
  - 运行入口代理

## 目标模型结构
- `app/models/{series,episode,shot,frame,ingest_job}.py`
- `frame` 是图片主索引结构，`shot` 是质检与文本对齐结构

## 禁止事项
- 不要再新增第二套模型元数据。
- 不要再恢复 `alembic/` 和根级 `workers/` 旧真值目录。
- 不要在 `app/services/` 外部复制新的 pipeline 逻辑。
