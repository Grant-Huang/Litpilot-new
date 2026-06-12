# 04 · SSE 事件契约（Meso v1.0）

> 本文定义 `GET /api/tasks/{id}/stream` 的流式契约：信封格式、事件类型、全部 extension 事件 payload、续传与看门狗。前端 SSE 解析器与后端推流器据此实现。

---

## 1. 信封格式

每个事件由标准 SSE 帧承载：`event: <type>` + `data: <json>`。后端在 data 中附加单调递增 `seq` 用于续传。

```
event: extension
data: {"seq":12,"name":"literature_search_plan","version":"1.0","data":{...}}

event: stage
data: {"seq":13,"name":"文献检索","state":"active"}

event: artifact
data: {"seq":14,"id":"review-latest","lang":"markdown","delta":"# 综述\n\n","done":false}

event: text
data: {"seq":15,"delta":"本文…","delivery":"process"}

event: done
data: {"seq":99}
```

> `seq` 从 1 递增，全任务唯一。`since=N` 表示"已收到 ≤N，请从 N+1 续推"。

## 2. 事件类型总表

| event | 用途 | data 字段 |
|-------|------|-----------|
| `stage` | 阶段切换时间线 | `name`（中文阶段名）、`state`：`active|done|error` |
| `text` | 聊天/流程文本增量 | `delta`、`delivery`：`chat|process` |
| `think` | Planner 流式解说（思考区） | `delta`；系统注记用 `⟦sys⟧…⟦/sys⟧` 包裹 |
| `artifact` | 产物增量 | `id`、`lang`、`delta`、`done`（见 §3） |
| `tool_call` | 工具开始 | `name`、`args`（截断） |
| `tool_result` | 工具结果 | `name`、`summary` |
| `extension` | LitPilot 自定义进度 | `name`、`version`、`data`（见 §4） |
| `done` | 流正常结束 | 空 |
| `error` | 流错误 | `message`、`code`? |

## 3. artifact 事件

| id | lang | 含义 |
|----|------|------|
| `review-latest` | `markdown` | 综述正文增量（`delivery=artifact`，逐章流式） |
| `matrix-latest` | `literature-matrix+markdown` | 文献矩阵 |
| `literature-outline` | `literature-outline+json` | 大纲（一般一次性 `done:true`） |

- `delta`：增量字符串；`done:false` 表示还有后续，`done:true` 表示该 artifact 完结。
- 前端按 `id` 累积；同 `id` 的多个 delta 顺序拼接。

## 4. extension 事件 payload（全量）

> 精简版保留与 3 意图相关的事件；移除 subtopic_change/revise 专属事件。

### 4.1 回合控制

| name | data |
|------|------|
| `turn_start` | `{ "turn_index": 2, "intent": "new_topic" }` 重置回合累积 |
| `turn_end` | `{ "turn_index": 2, "summary": {…turnWorkflow} }` 收尾回合（见 02 §3.2） |
| `session` | `{ "session_id": "…" }` 后端绑定/改写会话 ID |
| `session_title` | `{ "session_id": "…", "title": "…" }` 自动重命名，前端刷新列表 |

### 4.2 意图

| name | data |
|------|------|
| `literature_intent` | `{ "intent": "append_urls", "use_existing_corpus": true, "defer_generate": false }` |

### 4.3 检索

| name | data |
|------|------|
| `literature_search_plan` | `{ "count": 3, "subtopics": [{"id","title","search_query"}], "parallel_mode": "by_source", "source_parallel": 5, "topic_parallel": 3 }` |
| `literature_subtopic_plan` | `{ "subtopics": [{"id","title","search_query"}] }`（理解卡内计划视图） |
| `literature_search_pass_start` | `{ "pass_index": 2, "pass_total": 5, "query": "…", "topic_title": "…" }` |
| `literature_search_source_start` | `{ "source": "openalex", "label": "OpenAlex", "topic_title": "…" }` |
| `literature_search_source_done` | `{ "source": "openalex", "label": "OpenAlex", "topic_title": "…", "hits": 18, "state": "done|error" }` |
| `literature_subtopic_filter_done` | `{ "subtopic_id": "st1", "kept_count": 12, "rejected_count": 6 }` |
| `literature_search_merge` | `{ "total_before": 142, "total_after": 88 }`（去重合并） |

### 4.4 抓取

| name | data |
|------|------|
| `literature_fetch_start` | `{ "url_count": 43 }` |
| `literature_fetch_progress` | `{ "completed": 12, "failed": 4, "pending": 27 }` |
| `literature_fetch_done` | `{ "completed": 42, "failed": 3 }` |

### 4.5 进度/活动

| name | data |
|------|------|
| `literature_progress` | `{ "stage": "fetch", "elapsed_sec": 24, "parallel": 3, "in_flight": 5 }`（驱动并行度芯片与静默提示） |
| `literature_paper_index` | `{ "indexed": 42, "needs_attributes": 0 }`（结构化进度） |

### 4.6 大纲/章节

| name | data |
|------|------|
| `literature_outline` | （也可走 artifact）`{ "topic","sub_topics":[…],"sections":[…] }` |
| `literature_section_start` | `{ "section_id":"sec3","number":"三","title":"…" }`（分章写作开始） |

### 4.7 澄清/校验

| name | data |
|------|------|
| `literature_clarification` | `{ "kind": "first_turn|search_zero|outline_confirm", "prompt": "…", "options": ["…"] }` 触发澄清卡 |
| `literature_refine_report` | `{ "removed_cliches": N, "missing_sections": [], "todo_marks": M }`（后处理报告） |

## 5. 阶段名映射（stage.name → 流程卡 type）

| stage.name（中文） | 卡片 type |
|--------------------|-----------|
| 理解研究问题 | understand |
| 研究计划 | brief |
| 文献检索 | search |
| 抓取全文 | fetch |
| 引用抽取 | cite |
| 文献结构化 | attributes |
| 大纲规划 | outline |
| 综述生成 | generate |
| 文献矩阵 | matrix |
| 语料问答 | corpus_qa |
| 等待澄清 | clarify |
| 文献库操作 | manage |

## 6. 续传（since=N）

- 后端 `TaskManager` 为每个 task 保存全部已发事件（含 seq）。
- 连接 `?since=N`：先把 `seq > N` 的历史事件立即回放，再续推实时事件。
- task 已 `done/error`：回放全部历史后立即结束流。
- task 不存在：返回单个 `error` 事件 + 结束。

## 7. 看门狗与健壮性（前端 + 后端）

- **前端 rAF 批处理**：事件帧间累积，每帧最多一次 React 提交；`done/error` 同步落定。
- **前端看门狗**：收到响应头后 120s 无任何 chunk → abort，置错误态 + 重试按钮。
- **后端心跳**：长阶段（如抓取）每 ≤20s 至少发一个 `literature_progress`，避免前端误判冻结。
- **stream flush**：每个事件后 `flush`；禁用 Nginx/代理缓冲（`X-Accel-Buffering: no`）。

## 8. 前端消费状态机

```
idle → pending（POST /tasks 后等首字节）
     → streaming（收到首个事件）
     → settling（收到 done，物化 + 落盘回读中）
     → done / error
```

物化逻辑：
1. 累积 `stage`/`extension`/`tool_*` → 构建 `executionTrace`（WorkflowCard[]）。
2. 累积 `artifact` → review/matrix/outline 产物。
3. 累积 `text` → 聊天/流程文本。
4. `done` → 组装 `LitPilotMessage`（含 extras），`POST /api/sessions/{id}/messages` 落盘，再 `reloadSessionMessages` 回读校验（maxAttempts:5）。

## 9. 实现变更说明

### 9.1 前端 StreamState 结构（`lib/types.ts` 实际实现）

```typescript
interface StreamState {
  status: 'idle' | 'pending' | 'streaming' | 'settling' | 'done' | 'error';
  executionTrace: WorkflowCard[];   // 简化版 {stage, state, logs}
  artifacts: { review: string; matrix: string; outline: string };
  text: string;                     // 合并了原 chatText + processText
  think: string;                    // 独立思考区文本
  intent?: Intent;
  reviewVersion?: string;
  error?: string;
}
```

**关键变更**：
- `chatText`/`processText` 合并为统一的 `text` 字段（`reduceEvent` 中 `text` 事件不再区分 delivery）。
- 新增独立的 `think` 字段存储思考区内容（`think` 事件累积）。
- `WorkflowCard` 简化为 `{stage: string, state: CardState, logs?: string[]}`。

### 9.2 SSE 解析器（`lib/sse.ts` 实际实现）

- 使用 `fetch` + `ReadableStream` 手解析 SSE 帧（非 EventSource）。
- `reduceEvent` 函数：按事件类型更新 `StreamState`。
  - `stage` → 更新 `executionTrace`（通过 `updateTrace` 映射中文阶段名 → stage 标识）。
  - `text` → 累积到 `state.text`。
  - `think` → 累积到 `state.think`。
  - `artifact` → 按 id（review/matrix/outline）累积到对应 `artifacts` 字段。
  - `extension` → 处理 `literature_intent` 扩展事件。
  - `done` → 设置状态为 done，提取 reviewVersion。
  - `error` → 设置错误信息。
- `INITIAL_STATE` 导出常量用于重置状态。
- 看门狗：120s 超时 abort。
