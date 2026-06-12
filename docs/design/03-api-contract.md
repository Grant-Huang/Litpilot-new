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
| `GET /api/sessions/{id}/review?version=latest` | `{ "version": "v2", "markdown": "…", "versions": ["v1","v2"] }` |
| `GET /api/sessions/{id}/matrix` | `{ "markdown": "…" }` |
| `GET /api/sessions/{id}/outline` | `{ "outline": LiteratureOutline | null }` |
| `GET /api/sessions/{id}/library` | `{ "items": [LibraryItem] }`（本会话 provenance 过滤） |

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

> 路由前缀 `/library`（与 FRS 一致，不带 `/api`）；如统一前缀可在实现时加 `/api/library`，但需前后端一致。本文采用 `/library`。

### `GET /library/items`
- 响应 `data`: `{ "items": [LibraryItem] }`（按 display_index 升序，失败项可前置由前端排序）。

### `GET /library/items/{id}`
- 响应 `data`: `{ "item": LibraryItem, "full_text": "markdown | null" }`。

### `GET /library/tags`
- 响应 `data`: `{ "tags": [{"tag": "mom", "count": 7}] }`。

### `GET /library/items/{id}/related-sessions`
- 响应 `data`: `{ "sessions": [{"session_id","session_title","review_ref_index","initial_query"}] }`。

### `PATCH /library/items/{id}/star`
- 请求：`{ "starred": true }` → 响应 `{ "item": LibraryItem }`。

### `PATCH /library/items/{id}/tags`
- 请求：`{ "tags": ["mom","agent"] }`（≤20 个，每个 ≤48 字符，去重大小写不敏感）→ 响应 `{ "item": LibraryItem }`。

### `PATCH /library/items/{id}/metadata`
- 请求：`{ "doi"?: string, "url"?: string, "venue"?: string, "year"?: string, "volume"?, "issue"?, "pages"?, "publisher"?, "refresh_crossref"?: boolean }`
- 行为：保存书目；`refresh_crossref=true` 时重查 Crossref（无 DOI 先 OpenAlex 反查）。
- 响应：`{ "item": LibraryItem }`。

### `DELETE /library/items/{id}`
删除单条（连带 `sources/{id}.md`）。响应 `{ "deleted": true }`。

### `DELETE /library/items`
清空。响应 `{ "deleted_count": N }`。

### `POST /library/items/{id}/enrich`
按 DOI 富化（OpenAlex/Crossref）。响应 `{ "item": LibraryItem }`。

### `POST /library/refresh-metadata`
批量并行刷新。
- 请求：`{ "item_ids"?: [string], "parallel": 4 }`（parallel 1–12）。
- 响应：`{ "updated_count": N, "items": [LibraryItem] }`。

### `POST /library/reconcile`
从会话/产物补抽引用。
- 请求：`{ "session_id"?: string, "mode": "session|all|failed_only" }`。
- 响应：`{ "added": N, "merged": M }`。

### `GET /library/pdfs/{filename}`
返回 PDF 二进制（校验路径在 `pdfs/` 下，防目录穿越）。`Content-Type: application/pdf`。

---

## 5. 设置 Settings

### 个人偏好（精简版基本为空）
- `GET /api/settings/personal/preferences` → `{ }`（精简版无字段；保留端点返回空对象）。
- `PUT /api/settings/personal/preferences` → 接受空体；返回 `{ }`。

> 说明：精简版移除 `citation_format`。前端个人页展示只读说明「引用格式固定为 APA」。

### 概览
- `GET /api/settings/system/overview` → `data`:
```jsonc
{
  "capabilities": [{"capability_id":"review_main","label":"综述主模型","status":"ok|pending","summary":"deepseek-v4 · …"}],
  "credentials": [{"id","type","name","status"}],
  "instances": [{"id","name","provider","model_name"}],
  "storage": {"backend":"local|turso|hybrid","status":"ok|pending","tenant_id":"default"}
}
```

### 存储
- `GET /api/settings/system/storage` → `{ "has_auth_token": bool, "masked_auth_token": "··· ab12", "database_url": "…", "url_source":"env|admin|none", "token_source":"…", "turso_ready": bool, "backend":"local|turso", "tenant_id":"default" }`
- `PUT /api/settings/system/storage` → 请求 `{ "database_url"?: string, "auth_token"?: string }`（token 空串=移除，省略=不改）。

### 凭据
- `GET /api/settings/system/credentials` → `{ "items": [Credential（掩码）] }`
- `POST /api/settings/system/credentials` → 请求 `{ "type", "name", "secret"?, "base_url"?, "group_id"? }`（201）
- `GET /api/settings/system/credentials/{id}`
- `PUT /api/settings/system/credentials/{id}` → `{ "name"?, "secret"?, "base_url"?, "group_id"? }`（secret 空串=清除→status unknown；改 secret 时 last_verified_at=null）
- `DELETE /api/settings/system/credentials/{id}`（被实例引用 → 409）
- `POST /api/settings/system/credentials/{id}/test` → 请求 `{ "query"?: string }`（默认 `"transformer attention paper arxiv"`）→ `{ "ok": bool, "message": "…", "hits"?: N, "tested_at": "…" }`

Credential 公开结构：
```jsonc
{ "id","type","name","has_secret":true,"masked_secret":"··· 1a2b",
  "base_url":"https://api.deepseek.com/v1","group_id":"",
  "status":"ok|fail|unknown","last_verified_at":"…","created_at":"…","updated_at":"…" }
```

### 实例
- `GET /api/settings/system/instances` → `{ "items": [Instance] }`
- `POST /api/settings/system/instances` → `{ "name","credential_id","model_name","default_params"? }`（201）
- `GET/PUT/DELETE /api/settings/system/instances/{id}`（被能力引用 → 409）
- `POST /api/settings/system/instances/{id}/test` → 绑定校验 → `{ "ok": bool, "message": "已通过基础检查" }`

### 能力
- `GET /api/settings/system/capabilities` → `{ "items": [Capability] }`
- `PUT /api/settings/system/capabilities/{capability_id}` → `{ "primary_ref"?: {"kind":"credential|instance","id":"…"}, "params"?: {…}, "enabled"?: bool }`
- `POST /api/settings/system/capabilities/web_fetch/test` → 请求 `{ "url"?: string }` → `{ "ok": bool, "provider","raw_bytes","text_chars","is_pdf","title"?,"preview": "前1200字" }`
- `POST /api/settings/system/capabilities/web_search/test` → 请求 `{ "query"?: string }` → `{ "ok": bool, "provider","hits": N, "results": [前3条] }`

### Prompts 默认与元数据
- `GET /api/settings/system/prompts/defaults` → `{ "defaults": {"<key>": "模板"}, "meta": [{"key","label","group","hint","max_len","default_max_tokens","max_tokens_limit"}] }`
- Prompts 保存复用 `PUT /api/settings/system/capabilities/{prompts|orchestrator|review_main}`（见 06）。

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
