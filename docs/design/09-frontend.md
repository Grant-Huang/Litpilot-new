# 09 · 前端设计详设

> 对应 plan todo `frontend`。本文定义 Next.js（App Router + TypeScript）前端的三大界面、组件清单、状态管理、SSE 消费、产物渲染，以及 brand kit 接入。后端契约见 03/04。

---

## 1. 技术栈与目录

- Next.js 16.2.9 LTS（App Router）+ TypeScript + React 19。
- 样式：Tailwind CSS + `docs/brand/tokens.css`（CSS 变量）。
- Logo：`docs/brand/react/LitPilotMark.tsx`（零依赖组件）。
- 全局通知：`ToastProvider`（info/success/error 三级）。

```
frontend/
├── app/
│   ├── layout.tsx                 # 全局布局 + ToastProvider + Geist 字体 + brand tokens
│   ├── page.tsx                   # 重定向到 /chat
│   ├── chat/
│   │   ├── page.tsx               # 主聊天页（使用 ChatShell 无 initialSessionId）
│   │   └── [sessionId]/page.tsx   # 动态路由聊天页（使用 ChatShell + initialSessionId）
│   ├── library/page.tsx           # 文献库（完整实现：搜索/筛选/标签/详情/编辑）
│   └── settings/
│       ├── layout.tsx             # 设置侧栏导航
│       ├── personal/page.tsx      # 个人设置（只读说明）
│       └── admin/
│           ├── page.tsx           # 系统概览
│           ├── storage/page.tsx   # 存储配置表单
│           ├── credentials/page.tsx # 凭据管理（编辑/保存/测试）
│           ├── instances/page.tsx  # LLM 实例 CRUD + 测试
│           ├── capabilities/page.tsx # 能力绑定选择器
│           └── prompts/page.tsx    # 提示词编辑器
├── components/
│   ├── ToastProvider.tsx          # 全局 Toast 通知（固定定位右下角）
│   ├── NavSidebar.tsx             # 导航侧栏（/chat, /library, /settings）
│   ├── LitPilotMark.tsx           # 品牌 Logo
│   ├── chat/
│   │   ├── ChatShell.tsx          # 共享聊天逻辑（会话管理/SSE/发送）
│   │   ├── SessionList.tsx        # 会话列表（重命名/删除/置顶/菜单）
│   │   ├── MessageArea.tsx        # 消息渲染（rAF 批处理/澄清卡/流式文本）
│   │   ├── WorkflowCard.tsx       # 流程卡片（日志行展开/折叠）
│   │   ├── TurnCompletionBar.tsx  # 回合完成统计栏
│   │   └── Composer.tsx           # 输入器（文本/URL/文件上传）
│   └── artifact/
│       └── ArtifactPanel.tsx      # 产物面板（大纲/综述/矩阵/文献 Tab）
├── lib/
│   ├── api.ts                     # REST 客户端（完整 CRUD：sessions/library/settings）
│   ├── sse.ts                     # SSE 解析 + reduceEvent 状态机 + connectStream
│   └── types.ts                   # TypeScript 类型（与 02/04 对齐）
└── styles/
    └── tokens.css                 # brand tokens CSS 变量
```

## 2. /chat 四列布局

```
┌ 导航(≈145px) ┬ 会话列表(≈260px) ┬ 中间对话区(flex) ┬ Artifact 面板 ┐
```

- 左两栏合计约 405px 固定。
- 中间对话区主内容 `max-width: min(72rem, max(42rem, 主列宽 × 0.68))`。
- Artifact 打开时宽 `clamp(280px, 主列宽 - 内容宽 - 32px, 420px)`，根节点加 `litpilot-layout--artifact-open`，主内容收窄。

### 2.1 会话列表
- 展示标题、置顶在前；操作：新建/选择/重命名/删除/置顶。
- 激活会话存 `localStorage['litpilot:active-session']`，加载恢复；`/chat/{id}` 直开。

### 2.2 消息区
- 空状态欢迎屏（LitPilot 标识 + 引导语）。
- 历史渲染：
  - user → `ChatBubble role=user`。
  - assistant 含 `extras.executionTrace|turnWorkflow` → `AssistantTurn`（流程卡片 + 可选气泡）。
  - assistant 纯文本 → `ChatBubble role=assistant`。
- 气泡显示条件：`delivery==="chat"` 且正文非空 且 `artifactKind!=="review"`。
- 自动滚动：贴底阈值 80px；上滑暂停；切会话重新贴底；ResizeObserver 监听；不在底显示"回到底部" FAB。

### 2.3 WorkflowCard
- props：`{type, title, state, summary, steps, tree?}`。
- 状态图标：pending ○ / running ⟳(spin) / done ✓ / error ⚠。
- 默认展开：`state==='running'` 或 `type==='clarify'`（强制）。
- LogRow：`{kind, state, text, result?, detail?}`；有 detail 时 chevron 展开 `<pre>`。
- `SearchProgressView`：渲染 `tree`（子主题 → 数据源行 → 过滤明细），见 02 §3.3。

### 2.4 TurnCompletionBar
- 标题行（聚合统计）+ 简评行（弱子主题）+ CTA「综述已生成 [查看综述]」（产物存在且面板未开时）。

### 2.5 Composer
- 多行 textarea（2–6 行）；回车发送、Shift+回车换行；流式禁用。
- 占位「描述你的研究主题或综述问题…」。
- 链接上传「+」：`.txt/.csv/.json` 解析 http(s)；**首轮禁用，第 2 轮起启用**；超 `max_fetch_urls` 截断 + Toast。
- 发送启用：`(文本非空 || (有链接 && 非首轮)) && 非流式`。
- 流式中→「■ 停止」(DELETE task)。
- 静默提示（`silenceSec`：<5 不提示 / 5–19 waiting / ≥20 slow）；并行度芯片（从 `literature_search_plan`/`literature_progress` 提取，只读）。

## 3. SSE 消费与流状态机（`lib/sse.ts` 实际实现）

```
idle → pending → streaming → settling → done|error
```

- `fetch` + `ReadableStream` 手解析 SSE 帧（`event:`/`data:` 行）。
- `connectStream(taskId, since, onEvent, onDone, onError)` → 返回 `AbortController`。
- `reduceEvent(state, event)` → 按事件类型更新 `StreamState`：
  - `stage` → `updateTrace` 映射中文阶段名为 stage 标识，更新 `executionTrace`。
  - `text` → 累积到 `state.text`（不区分 delivery）。
  - `think` → 累积到 `state.think`。
  - `artifact` → 按 id 累积 delta 到对应 artifacts 字段。
  - `extension` → 处理 `literature_intent` 设置 intent。
  - `done` → 设置 status=done，提取 reviewVersion。
  - `error` → 设置错误信息。
- `INITIAL_STATE` 常量导出用于重置。
- 120s 看门狗：每 chunk 重置计时器；超时 abort + 错误态。
- rAF 批处理：`MessageArea` 组件内用 `requestAnimationFrame` 包裹 `setStream` 状态更新，每帧最多一次 React 提交。

## 4. Artifact 面板（四 Tab）

| Tab | 组件 | 数据源 |
|-----|------|--------|
| 大纲 | 内联渲染 | artifact `literature-outline+json` / `GET /sessions/{id}/outline` |
| 综述 | 内联渲染 | artifact `markdown` + `GET /sessions/{id}/review` |
| 矩阵 | 内联渲染 | artifact `literature-matrix+markdown` / `GET /sessions/{id}/matrix` |
| 文献 | 内联渲染 | `GET /api/library`（全局文献库） |

- 综述 Tab：导出按钮（复制/下载 .md）。**不做版本下拉选择器**，始终展示最新版本。
- 矩阵 Tab：渲染 markdown 表格。
- 文献 Tab：全局文献库条目列表。
- 可见性：存在综述/matrix/outline 产物即显示面板。
- 流式中钉住产物；流结束保持；切会话重置重载。

## 5. /library 文献库（两栏）

- 头部：标题 + "共 {count} 条" + "刷新元数据"（并行 1–12，默认 4 → `POST /library/refresh-metadata`）。
- 左栏列表：
  - 搜索框（多字段子串：标题+作者+URL+DOI+出处+年份+APA+display_index+标签）。
  - 筛选芯片（全部/有全文/失败/收藏/本会话）。
  - 标签过滤条（多选 OR，计数来自 `GET /library/tags`）。
  - 结果计数；排序失败优先 + display_index。
- `LibraryRefCard`：`[index] 标题`、作者行、出处/年份/被引-他引、标签(≤3+n)、引用复制（**仅 APA**）、收藏 ★、删除、徽标行（抓取失败/引用失败/全文/PDF/DOI/原文/N 个综述）。
- 右栏 `LibraryDetailPane` Tab：摘要(始终)/全文(has_full_text)/元数据(始终)/综述(provenance)/PDF(has_pdf)。
  - `DoiEditor`：保存 `PATCH /metadata`（可 refresh_crossref）。
  - `TagEditor`：`PATCH /tags`（≤20 个，≤48 字符，去重）。
- 列表可缓存 ~30s，允许强制刷新。

## 6. /settings

### 6.1 个人（精简版）
- 只读说明卡：「引用格式固定为 APA（本版本不可切换）」。无可保存字段。

### 6.2 管理员（实际实现）
| 分组 | 项 | 路由 | 功能 |
|------|----|------|------|
| System | 概览 | `/settings/admin` | Python 版本/存储模式/统计卡片（凭据/实例/能力/文献/会话数） |
| System | 存储 | `/settings/admin/storage` | 存储模式/数据目录/最大空间 表单 + 保存 |
| Connect | 凭据 | `/settings/admin/credentials` | 7 种凭据编辑 + 掩码显示 + 测试按钮 + 保存 |
| Connect | 实例库 | `/settings/admin/instances` | LLM 实例 CRUD 表单（provider/model/baseURL/key/tokens/temp）+ 测试 + 删除 |
| Capability | 检索与抓取 | `/settings/admin/capabilities` | 5 类能力绑定下拉选择 + 保存 |
| Capability | 编排与综述 | `/settings/admin/prompts` | 4 个提示词 textarea 编辑器 + 保存/重置 |

**关键实现**：
- 每个管理页均为 'use client' 组件，通过 `api.*` 客户端与后端 CRUD 端点交互。
- 凭据页：支持 7 种预定义密钥（OpenAI/DeepSeek/MiniMax/Tavily/Brave/Jina/Semantic Scholar）。
- 实例页：完整 CRUD（新增/编辑/删除）+ 连接测试按钮。
- 能力页：下拉选择绑定的 LLM 实例。
- 提示词页：按阶段分组的 textarea 编辑器，支持独立保存和重置。
- 所有保存操作使用 `useToast` 提供操作反馈。

## 7. 类型定义（`lib/types.ts` 实际实现，与 02/04 对齐）

```typescript
type Delivery = "chat" | "process" | "artifact";
type CardState = "pending" | "running" | "done" | "error";
type Intent = "new_topic" | "append_urls" | "query_corpus";

// 简化版 WorkflowCard（实际实现）
interface WorkflowCard { stage: string; state: CardState; logs?: string[]; }

interface LitPilotMessage {
  id: string; session_id: string; role: "user"|"assistant";
  content: string; created_at: string; extras?: MessageExtras;
}

interface MessageExtras {
  delivery?: Delivery;
  artifactKind?: "review"|"matrix"|"outline"|"none";
  intent?: Intent;
  executionTrace?: WorkflowCard[];
  review_version?: string;
  clarification?: string;   // 澄清卡提示文本
}

// SSE 流状态（实际实现）
interface StreamState {
  status: 'idle' | 'pending' | 'streaming' | 'settling' | 'done' | 'error';
  executionTrace: WorkflowCard[];
  artifacts: { review: string; matrix: string; outline: string };
  text: string;     // 合并了 chatText + processText
  think: string;    // 思考区独立
  intent?: Intent;
  reviewVersion?: string;
  error?: string;
}

const INITIAL_STATE: StreamState;   // 初始空状态常量

interface SessionMeta {
  id: string; title: string; created_at: string; updated_at: string;
  user_turns: number; has_review: boolean; has_matrix: boolean;
  initial_query?: string; last_intent?: Intent; pinned?: boolean;
}

interface LibraryItem {
  display_index: number; title: string; authors: string; year: string;
  doi: string; url: string; apa_citation: string; venue: string;
  abstract: string; tags: string[]; has_full_text: boolean;
  has_pdf: boolean; fetch_status: string; canonical_key: string;
}

interface LLMInstance {
  id: string; name: string; provider: string; model: string;
  base_url: string; api_key_set: boolean; max_tokens: number; temperature: number;
}

interface CapabilityBinding { capability: string; instance_id: string; instance_name?: string; }

interface PromptConfig { name: string; system_prompt: string; temperature?: number; max_tokens?: number; }
```

**关键变更**：
- `WorkflowCard` 简化为 `{stage, state, logs}`（移除 `type/title/summary/steps/tree`）。
- `StreamState.text` 合并了原 `chatText` + `processText`；新增 `think` 独立字段。
- `MessageExtras` 新增 `clarification` 字段（澄清卡提示）。
- 新增 `LLMInstance`、`CapabilityBinding`、`PromptConfig`（管理页面所需）。

## 8. 错误与边界（FRS §1.10）

| 场景 | 处理 |
|------|------|
| SSE 超时 | 120s 看门狗 abort → 错误态 + 重试 |
| event:error | Toast 错误详情 + 重试 |
| 停止 | DELETE task → 清流回 idle |
| 部分抓取失败 | 完成栏「42 成功 / 3 失败」 |
| 零命中无链接 | clarify 卡（search_zero） |
| 流式中切会话 | 中止当前流、清实时消息、加载新会话 |
| 上滑阅读 | 暂停自动滚动 |

## 9. TDD / 测试要点（前端）

- 单测（Vitest/RTL）：`stream-reducer`（事件→trace/artifact 累积）、Composer 发送启用逻辑、气泡显示判定、版本下拉。
- 组件测试：WorkflowCard 展开/状态图标、LibraryRefCard 徽标优先级。
- e2e（可选 Playwright）：发起综述 → 看到流程卡片 → Artifact 出现综述 → 文献库出现条目。

## 10. brand 接入清单

- `app/layout.tsx`：引入 Geist/Geist Mono 字体 + `tokens.css`；favicon 用 `docs/brand/snippets/head.html`。
- Logo：`LitPilotMark.tsx`；色彩用 `--lp-ink`/`--lp-accent` 等 token，accent 仅用于 CTA/品牌点缀。
