# 09 · 前端设计详设

> 对应 plan todo `frontend`。本文定义 Next.js（App Router + TypeScript）前端的三大界面、组件清单、状态管理、SSE 消费、产物渲染，以及 brand kit 接入。后端契约见 03/04。

---

## 1. 技术栈与目录

- Next.js（App Router）+ TypeScript + React 18。
- 样式：接入 `docs/brand/tokens.css`（CSS 变量）与 `docs/brand/tailwind.tokens.js`（如用 Tailwind）。
- Logo：`docs/brand/react/LitPilotMark.tsx`（零依赖组件）。

```
frontend/
├── app/
│   ├── layout.tsx                 # 全局布局、字体(Geist)、brand tokens
│   ├── page.tsx                   # 重定向到 /chat
│   ├── chat/[[...sessionId]]/page.tsx
│   ├── library/page.tsx
│   └── settings/
│       ├── layout.tsx             # 设置侧栏
│       ├── personal/page.tsx
│       └── admin/{page,storage,credentials,instances,capabilities,prompts}/page.tsx
├── components/
│   ├── chat/ (ChatBubble, AssistantTurn, WorkflowCard, LogRow, SearchProgressView, TurnCompletionBar, Composer)
│   ├── artifact/ (ArtifactPanel, OutlineView, ReviewView, MatrixView, LiteratureView)
│   ├── library/ (LibraryListPanel, LibraryRefCard, LibraryDetailPane, DoiEditor, TagEditor)
│   └── settings/ (InlineField, InlineCheck, FieldTip, SettingToolbar, SettingsListPanel)
├── lib/
│   ├── api.ts                     # REST 客户端（统一响应解包）
│   ├── sse.ts                     # SSE 解析 + 流状态机
│   ├── stream-reducer.ts          # 事件 → executionTrace/artifact 累积
│   ├── types.ts                   # 与 02/03/04 对齐的 TS 类型
│   └── store.ts                   # 会话/激活态（localStorage litpilot:active-session）
└── styles/
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

## 3. SSE 消费与流状态机（`lib/sse.ts` + `stream-reducer.ts`）

```
idle → pending → streaming → settling → done|error
```

- `EventSource` 不支持自定义 since header，故用 `fetch` + `ReadableStream` 手解析 `event:`/`data:`。
- rAF 批处理：事件入队，`requestAnimationFrame` 每帧最多一次 setState；`done/error` 同步 flush。
- 120s 看门狗：每 chunk 重置；超时 abort + 错误态 + 重试。
- reducer 把事件累积成：
  - `executionTrace: WorkflowCard[]`（按 stage/extension 映射，见 04 §5）。
  - `artifacts: { review, matrix, outline }`（按 artifact id 累积 delta）。
  - `chatText` / `processText`（按 delivery）。
  - `turnWorkflow`（来自 `turn_end`）。
- `done` → 组装 `LitPilotMessage`，落盘 + 回读（见 08 §5）。

## 4. Artifact 面板（四 Tab）

| Tab | 组件 | 数据源 |
|-----|------|--------|
| 大纲 | `OutlineView` | artifact `literature-outline+json` / `GET /sessions/{id}/outline` |
| 综述 | `ReviewView` | artifact `markdown` + `GET /sessions/{id}/review?version=` |
| 矩阵 | `MatrixView` | artifact `literature-matrix+markdown` / `GET /sessions/{id}/matrix` |
| 文献 | `LiteratureView` | `GET /sessions/{id}/library` |

- `ReviewView`：版本下拉（latest/v1/v2…）+ 导出（下载 .md / 复制）。
- `MatrixView`：渲染 markdown 表格。
- `LiteratureView`：本会话条目，可按 `subtopic_tags` 筛选、复制 APA。
- 可见性：存在综述即有面板；未打开时轻推动画（~4s 脉冲）+ 完成栏 CTA。
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

### 6.2 管理员侧栏
| 分组 | 项 | 路由 |
|------|----|------|
| System | 概览 | `/settings/admin` |
| System | 存储 | `/settings/admin/storage` |
| Connect | 凭据 | `/settings/admin/credentials` |
| Connect | 实例库 | `/settings/admin/instances` |
| Capability | 检索与抓取 | `/settings/admin/capabilities` |
| Capability | 编排与综述 | `/settings/admin/prompts` |

- 共享组件：`InlineField`/`InlineCheck`/`FieldTip`/`SettingToolbar`（标题|状态徽标|反馈|操作）/`SettingsListPanel`。
- 状态徽标：ok=绿 / fail=红 / pending|unknown=灰。
- 离开守卫：dirty 时离页提醒。
- 凭据 API Key 字段：已存在显示掩码，聚焦可编辑，失焦留空回退掩码。
- 能力页字段表见 FRS §4.6（web_search/web_fetch 参数、约束、默认值）；底部 Web 连通测试面板。
- Prompts 页：按阶段分组，每条 = 模板 textarea + max_tokens + 实例下拉；全局保存条（dirty）。

## 7. 类型定义（`lib/types.ts` 摘要，与 02/04 对齐）

```typescript
type Delivery = "chat" | "process" | "artifact";
type CardType = "understand"|"brief"|"search"|"fetch"|"cite"|"attributes"|"outline"|"generate"|"matrix"|"corpus_qa"|"clarify"|"manage";
type CardState = "pending"|"running"|"done"|"error";
type Intent = "new_topic"|"append_urls"|"query_corpus";

interface WorkflowCard { type: CardType; title: string; state: CardState; summary?: string; steps: LogStep[]; tree?: SearchTree; }
interface LogStep { kind: "tool"|"inline"|"think"; state: CardState; text: string; result?: string; detail?: string; }
interface LitPilotMessage { id: string; session_id: string; role: "user"|"assistant"; content: string; created_at: string; extras?: MessageExtras; }
interface MessageExtras { delivery?: Delivery; artifactKind?: "review"|"matrix"|"outline"|"none"; intent?: Intent; executionTrace?: WorkflowCard[]; turnWorkflow?: TurnWorkflow; review_version?: string; }
```

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
