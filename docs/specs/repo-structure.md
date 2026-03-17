# 仓库结构规范

## 主结构
- `app/`
  - `api/` HTTP 路由
  - `core/` 配置与默认值
  - `db/` engine、session、基础类型
  - `models/` ORM 模型
  - `schemas/` Pydantic 输入输出
  - `services/` manifest、pipeline、检索、Gemini、队列
- `workers/`
  - 根级兼容 worker 入口
- `alembic/`
  - 主迁移目录
- `docs/specs/`
  - 实现级规格文档
- `tests/`
  - 单元测试
- `scripts/`
  - 运行入口代理

## 兼容层说明
- `app/models/{series,episode,scene,shot,frame,ingest_job}.py`
  - 作为兼容导入壳
  - 源事实模型在 `app/models/media.py` 与 `app/models/job.py`
- `app/workers/`
  - 作为兼容入口
  - 实际任务执行入口在根目录 `workers/`

## 禁止事项
- 不要再新增第二套模型元数据。
- 不要在 `migrations/` 和 `alembic/` 同时演进不同 schema。
- 不要在 `app/services/` 外部复制一份新的 pipeline 逻辑。
