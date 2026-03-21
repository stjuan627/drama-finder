# Drama Finder

基于 `FastAPI + PostgreSQL + pgvector + Redis/RQ` 的中文剧集截图定位系统。

当前仓库已初始化：

- 后端服务骨架
- 数据库模型与迁移骨架
- manifest 校验与元数据同步
- 入库任务编排骨架
- shot/segment 方案的过渡实现骨架
- 规格文档目录

详细方案见 [docs/general-plan.md](docs/general-plan.md) 和 [AGENTS.md](AGENTS.md)。

## 本地启动

1. 启动基础设施

```bash
docker compose -f compose.yaml up -d
```

2. 安装依赖

```bash
env UV_CACHE_DIR=.uv-cache uv sync --extra dev --extra pipeline
```

3. 执行迁移

```bash
.venv/bin/alembic upgrade head
```

4. 启动 API

```bash
.venv/bin/python scripts/run_api.py
```

5. 启动 worker

```bash
.venv/bin/python scripts/run_worker.py
```
