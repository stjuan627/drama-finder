# React 前端迁移计划

## 目标

- 用 `React + TypeScript` 重写当前 Python 内联 demo 页。
- 保持 `FastAPI` 作为唯一后端与同域静态托管入口。
- 第一阶段只覆盖现有两页能力：`搜索页` 与 `入库页`。
- 保持当前 API 契约不变：`/search/text`、`/search/image`、`/ingest/episode`、`/ingest/{job_id}`、`/demo/evidence`。

## 非目标

- 不做独立前后端分仓。
- 不重命名当前 API 路径，不统一加 `/api` 前缀。
- 不引入 `WebSocket` 或 `SSE`，入库页继续使用轮询。
- 不扩展到管理台、评测页、认证系统或对象存储。
- 不在首轮迁移中重做检索/入库业务逻辑。

## 托管与路由策略

- 前端目录固定为 `frontend/`。
- React 构建产物固定输出到 `frontend/dist/`。
- FastAPI 在运行时挂载构建产物，并提供：
  - `GET /ui/search`
  - `GET /ui/ingest`
- 切流前保留当前页面：
  - `GET /`
  - `GET /search`
  - `GET /ingest`
  - `GET /demo`
- 切流后：
  - `GET /`、`GET /search`、`GET /ingest` 指向 React 页面
  - `GET /demo` 保留为轻量回退与路由检查页，不再承载旧版完整 demo 功能
  - `GET /demo/evidence` 继续由后端负责，禁止前端直连本地文件路径

## 当前实现状态

- React 已接管默认入口：`/`、`/search`、`/ingest`
- `GET /ui/search` 与 `GET /ui/ingest` 仍可单独访问，适合联调与 smoke test
- `GET /demo` 现在是轻量说明页与跳转页，不再保留原来那套 1000 行内联 HTML/CSS/JS，也不再提供旧版完整页面交互
- `GET /demo/evidence` 保持不变，继续为 React 结果页提供证据图代理

## 启动方式

### 构建后通过 FastAPI 访问

```bash
cd frontend
npm install
npm run build
cd ..
make start
```

访问：

- `http://127.0.0.1:8000/search`
- `http://127.0.0.1:8000/ingest`

如果未先生成 `frontend/dist/`，那么 `8000` 下只会返回 React shell 提示页；这是正常行为，需要先执行 `npm run build`。

### 开发模式

先启动 API：

```bash
make start
```

再启动 Vite：

```bash
cd frontend
npm install
npm run dev
```

访问：

- `http://127.0.0.1:5173/ui/search`
- `http://127.0.0.1:5173/ui/ingest`

如果要验证真实入库任务推进，还需要额外启动 `make worker`。

## React 页面范围

### 搜索页

- 文本检索表单
- 截图上传与图片检索
- 结果列表
- 低置信提示
- 空结果提示
- 错误提示
- 证据图展示

### 入库页

- `manifest_path`、`series_id`、`episode_id` 表单
- 提交入库任务
- 轮询 `job` 状态
- 展示阶段、进度、错误信息
- 展示图片向量状态与子进度
- 保留 `localStorage` 中的 `demo.jobId`

## PR 拆分

### PR1：脚手架与 FastAPI 接入

- 新建 `frontend/`，使用 `Vite + React + TypeScript`
- 提供 `SearchPage` 与 `IngestPage` 壳页面
- FastAPI 提供 `frontend/dist/` 静态资源与 `ui` 页面入口
- 保持旧 demo 页面不变

### PR2：搜索页迁移

- 实现文本检索
- 实现图片检索
- 渲染结果列表与证据图
- 覆盖 loading / empty / low-confidence / error 状态
- 先挂载到 `/ui/search`

### PR3：入库页迁移

- 实现提交任务
- 实现手动刷新任务状态
- 展示 embedding 状态与进度
- 保留 `demo.jobId` 恢复逻辑
- 挂载到 `/ui/ingest`

### PR4：切流与保底回退

- 将 `/` 与 `/search` 切换到 React 搜索页
- 将 `/ingest` 切换到 React 入库页
- `GET /demo` 继续保留旧页面

### PR5：清理旧内联页面

- 删除 `demo.py` 中不再使用的内联 HTML/CSS/JS
- 保留 `demo/evidence` 文件代理逻辑
- 更新测试到新的页面与契约基线
- 当前已完成

## 验收标准

- `GET /ui/search`、`GET /ui/ingest` 在切流前可直接访问
- 搜索页可完成文本检索与图片检索
- 入库页可提交任务并查看状态
- 结果仍以 `剧集 + 时间区间` 为主返回形态
- 证据图继续通过 `GET /demo/evidence` 安全访问
- 切流后 `GET /demo` 仍可作为旧版回退入口

## 风险与注意事项

- `ingest` 页面当前依赖 `artifacts.embedding_status` 与 `artifacts.embedding_progress`，前端必须按现状兼容。
- 页面路由与 API 路径同域共存，首轮不引入复杂客户端深路由。
- 旧测试目前依赖 HTML 文案断言，迁移后需要改为页面壳与回退行为断言。
