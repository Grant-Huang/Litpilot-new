# 03 · REST API 契约

> 本文定义全部 REST 端点的请求体、响应体、状态码与错误约定。**开发期冻结**，前后端据此独立开发。SSE 流契约见 [04-sse-events.md](./04-sse-events.md)。

---

## 1. 通用约定

### 1.1 统一响应结构（除 SSE 与 PDF 二进制外）

```jsonc
{ "status": "success", "data": { /* 业务数据 */ }, "message": "可选" }
{ "status": "error",   "data": null, "message": "错误描述" }
```

部分内部接口（设置测试等）可直接返回 `{ "ok": true, ... }`；同一接口风格保持一致即可。

### 1.2 状态码

| 码 | 含义 |
|----|------|
| 200 | 成功 |
| 201 | 创建成功（POST 资源） |
| 400 | 请求体校验失败 |
| 404 | 资源不存在 |
| 409 | 冲突（如删除被引用的凭据/实例） |
| 422 | FastAPI 参数校验（pydantic） |
| 500 | 服务端错误 |

### 1.3 通用错误体

```jsonc
{ "status": "error", "data": null, "message": "凭据被实例引用，无法删除" }
```

### 1.4 时间/ID

时间 ISO8601 UTC；ID 见 02 文档 §11。

---

## 2. 会话 Sessions

### `GET /api/sessions`
列出全部会话。
- 响应 `data`: `{ "sessions": [SessionMeta] }`（SessionMeta 见 02 §2，按 pinned 优先、`updated_at` 倒序）。

### `POST /api/sessions`
创建会话。
- 请求：`{ "title": "可选" }`
- 响应 `data`: `{ "session": SessionMeta }`（201）。

### `GET /api/sessions/{id}/messages`
- 响应 `data`: `{ "messages": [LitPilotMessage] }`（按 created_at 升序；见 02 §3）。

### `POST /api/sessions/{id}/messages`
追加并持久化一条消息（前端物化后回写）。
- 请求：`LitPilotMessage`（不含 id 时后端生成）。
- 响应 `data`: `{ "message": LitPilotMessage }`（201）。

### `PATCH /api/sessions/{id}`（兼容 `PUT`）
重命名 / 置顶。
- 请求：`{ "title"?: string, "pinned"?: boolean }`
- 响应 `data`: `{ "session": SessionMeta }`。

### `DELETE /api/sessions/{id}`
删除会话（连带目录）。
- 响应 `data`: `{ "deleted": true }`。

### 会话产物只读端点

| 端点 | 响应 data |
|------|-----------|
| `GET /api/sessions/{id}/review` | `{ "version": "v2", "content": "…综述 markdown…" }`（返回最新版本，不做版本选择） |
| `GET /api/sessions/{id}/matrix` | `{ "content": "…" }` |
| `GET /api/sessions/{id}/outline` | `{ …LiteratureOutline \| {} }` |

> **变更说明**：移除了 `GET /sessions/{id}/library` 端点（本会话 provenance 过滤），实际通过 `GET /api/library` 获取全局文献库。review 端点不做版本参数，始终返回最新版本。

---

## 3. 任务 Tasks

### `POST /api/tasks`
创建并启动任务（后台异步执行，立即返回）。
- 请求：
```jsonc
{
  "session_id": "a1b2c3d4e5f60718",
  "message": "用户输入文本",
  "fetch_urls": ["https://…"]         // 可选；首轮必须为空/省略
}
```
- 校验：
  - `session_id` 必须存在。
  - 首轮（`user_turns ≤ 1`）若携带 `fetch_urls` → 400「首轮不接受链接上传」。
  - `fetch_urls` 超过 `max_fetch_urls` → 截断（后端按设置保留前 N，不报错）。
- 响应 `data`: `{ "task_id": "t_…", "session_id": "…" }`（201）。

### `GET /api/tasks/{id}/stream?since=N`
SSE 流（详见 04）。`since` 为已接收的最大事件 `seq`，断线重连续传。
- 响应：`text/event-stream`（不走统一 JSON 包装）。
- Header：`Cache-Control: no-cache`、`X-Accel-Buffering: no`（禁代理缓冲）。

### `GET /api/tasks/{id}/status`
轮询任务状态（SSE 不可用时降级）。
- 响应 `data`: `{ "status": "running", "error": null, "last_seq": 42 }`。

### `DELETE /api/tasks/{id}`
取消任务。
- 响应 `data`: `{ "cancelled": true }`。

---

## 4. 文献库 Library

> 路由前缀 `/api/library`（实际实现统一使用 `/api` 前缀）。

### `GET /api/library`
- 查询参数：`search`（可选，标题/作者/DOI 子串匹配）、`tags`（可选，逗号分隔，OR 逻辑）。
- 响应 `data`: `{ "items": [LibraryItem] }`（按 display_index 升序）。

### `GET /api/library/{key}`
- `key` 可以是 `canonical_key`（如 `doi:10.1145/xxx`）或 `item_id`。
- 响应 `data`: `{ …LibraryItem }`。

### `PATCH /api/library/{key}`
- 请求：`{ "doi"?: string, "tags"?: string[]|string, "title"?: string, "authors"?: string }`
- 行为：`tags` 为字符串时自动按逗号拆分为数组。
- 响应：`{ "data": LibraryItem }`。

### `POST /api/library/{key}/refresh`
- 刷新单条文献元数据（当前返回原数据占位）。
- 响应：`{ "data": LibraryItem }`。

> **变更说明**：实际实现的文献库 API 较原设计大幅简化，移除了 `items/{id}/related-sessions`、`star`、`tags`（单独）、`metadata`（单独）、`DELETE`、`refresh-metadata`（批量）、`reconcile`、`pdfs/{filename}` 等端点。标签编辑合并到通用 `PATCH` 端点。DOI 编辑通过 `PATCH` 的 `doi` 字段实现。

---

## 5. 设置 Settings

> **实际路由前缀**：`/api/settings/*`。以下是实际实现的端点。

### 个人偏好（精简版）
- 前端页面 `/settings/personal` 为只读说明「引用格式固定为 APA」。无后端端点。

### 概览与系统配置
- `GET /api/settings/system` → `data`:
```jsonc
{
  "python_version": "3.14.x",
  "data_dir": "…",
  "storage_mode": "local",
  "credential_count": N, "instance_count": N,
  "capability_count": N, "library_count": N,
  "session_count": N,
  "backend": "local", "tenant_id": "default",
  "database_url": "", "has_auth_token": false, "masked_auth_token": ""
}
```
- `PUT /api/settings/system` → 请求 `{ "storage_mode"?, "data_dir"?, "max_storage_mb"? }`。

### 凭据
- `GET /api/settings/credentials` → `{ "data": { "<key>": { "masked": "··· 1a2b" } } }`
- `PUT /api/settings/credentials` → 请求 `{ "<key>": "明文secret" }`（按 key 匹配或新建）
- `POST /api/settings/credentials/{key}/test` → `{ "data": { "ok": true, "message": "…" } }`（模拟测试）

> **变更说明**：实际实现按 key（如 `openai_api_key`）映射凭据，而非按 `id`。测试端点返回模拟结果。

### 实例
- `GET /api/settings/instances` → `{ "data": { "instances": [Instance] } }`
- `POST /api/settings/instances` → `{ "name", "provider", "model", "base_url", "api_key"?, "max_tokens"?, "temperature"? }`（201）
- `PATCH /api/settings/instances/{id}` → 部分更新
- `DELETE /api/settings/instances/{id}`
- `POST /api/settings/instances/{id}/test` → `{ "data": { "ok": true, "message": "…" } }`（模拟测试）

### 能力
- `GET /api/settings/capabilities` → `{ "data": { "bindings": [{ "capability", "instance_id", "instance_name" }] } }`
- `PUT /api/settings/capabilities/{capability}` → `{ "instance_id": "…" }`

### Prompts
- `GET /api/settings/prompts` → `{ "data": { "prompts": [{ "name", "system_prompt" }] } }`
- `PUT /api/settings/prompts/{name}` → 保存提示词覆盖（当前占位）

---

## 6. web_search / web_fetch 能力测试请求默认值

| 测试 | 默认值 |
|------|--------|
| credentials/{id}/test query | `transformer attention paper arxiv` |
| web_search/test query | `systematic literature review methods` |
| web_fetch/test url | 某 webmedia 文章（实现可配 `deploy.defaults.json`） |

## 7. CORS / 安全

- 开发期允许前端 `http://localhost:3000`；生产用环境变量配置允许源。
- 输入参数全部经 pydantic 校验；文献库 PDF 端点校验路径前缀，防穿越。
- 日志不打印 secret/token。
