# 00 · 需求汇总（精简版）

> 本文是 LitPilot 精简版的需求基线，从 [docs/functional-requirements-spec.md](../functional-requirements-spec.md)、[docs/flow-card-logic-and-prompts.md](../flow-card-logic-and-prompts.md)、[docs/tools-reference.md](../tools-reference.md) 三份文档收敛而来，并冻结"精简版"决策。后续所有设计与实现以本文为准；与原 FRS 冲突时，以本文的"范围冻结"为准。

---

## 1. 产品定位

LitPilot 是面向科研人员的**文献综述助手**。用户用自然语言描述研究主题，系统自动完成：理解问题 → 学术检索 → 全文抓取 → 引用抽取 → 大模型综述生成 → 交付结构化产物（综述、文献矩阵、大纲），并把抽取到的引用沉淀进**文献库**。执行过程以"流程卡片"实时可视化。

## 2. 范围冻结（精简版核心决策）

| 维度 | 决策 | 说明 |
|------|------|------|
| 意图数量 | **3 类** | `new_topic`（首轮/完整流水线）、`append_urls`（追加链接重写综述）、`query_corpus`（基于已有综述/语料问答，兜底） |
| 引用格式 | **仅 APA** | 移除 ACM 与个人设置切换；底层 `citation_format` 参数恒为 `"apa"` |
| 版本规则 | **v(n+1)** | 每次产出新综述即 `v1, v2, v3…`，无 `a/b` 字母后缀 |
| 已删除分支 | `revise` / `subtopic_change` / `review_refine` / `short_answer` / `expand_search` / `retry_failed` / `manage_library` / `supplement` | 续聊路由仅在 `append_urls` 与 `query_corpus` 间二选一 |
| 个人设置 | 移除 `citation_format` 字段 | 个人设置页保留但置空或仅展示只读说明（见 09） |

> 决策依据：用户在规划阶段明确选择"按 flow-card 精简版"。

## 3. 三大界面

| 界面 | 路由 | 职责 |
|------|------|------|
| 主会话窗口 | `/chat`、`/chat/{sessionId}` | 文献综述对话、流程可视化、流式输出、右侧 Artifact 面板 |
| 文献库 | `/library` | 引用索引浏览、元数据编辑、按状态/标签筛选、APA 引用复制导出 |
| 设置-个人 | `/settings/personal` | 个人偏好（精简版下基本为空，保留页面） |
| 设置-管理员 | `/settings/admin/*` | 凭据、实例、能力（检索/抓取）、Prompts、存储 |

## 4. 功能需求（FR）

### FR-1 会话管理
- FR-1.1 会话 CRUD：新建、列出、选择、重命名、删除、置顶（pin）。
- FR-1.2 置顶会话排在普通会话前；列表项展示自动命名的标题。
- FR-1.3 当前激活会话持久化于前端 `litpilot:active-session`，加载时恢复。
- FR-1.4 路由 `/chat/{sessionId}` 直接打开指定会话。

### FR-2 对话与流式执行
- FR-2.1 空状态欢迎屏；历史消息分"用户气泡 / 助手回合（流程卡片）/ 助手纯文本"渲染。
- FR-2.2 助手文字气泡仅当 `delivery==="chat"` 且正文非空 且 `artifactKind !== "review"` 时展示。
- FR-2.3 流式中追加"实时回合"，含运行指示器；自动滚动贴底阈值 80px，上滑保留位置。
- FR-2.4 发送 → 创建 Task → 订阅 SSE → 物化助手消息 → 落盘 → 回读校验。

### FR-3 流程卡片可视化
- FR-3.1 卡片类型（精简版保留）：`understand` / `brief` / `search` / `fetch` / `cite` / `attributes` / `outline` / `generate` / `matrix` / `corpus_qa` / `clarify` / `manage`（移除 `revise`）。
- FR-3.2 卡片状态 `pending|running|done|error`；running 默认展开，`clarify` 强制展开。
- FR-3.3 日志行：`tool|inline|think` 三类，可展开详情；完成后给摘要文字。
- FR-3.4 多子主题时检索阶段渲染检索进度树。
- FR-3.5 回合完成栏：聚合统计 + 弱子主题简评 + "查看综述" CTA。

### FR-4 输入器（Composer）
- FR-4.1 多行自适应文本框（2–6 行），回车发送、Shift+回车换行，流式中禁用。
- FR-4.2 链接上传：接受 `.txt/.csv/.json` 解析 http(s) 链接；**首轮禁用，第 2 轮起启用**；超出 `max_fetch_urls`（默认 5，上限 50）截断并 Toast 提示。
- FR-4.3 流式中发送按钮变"停止"，点击取消任务。
- FR-4.4 静默提示（5–19s waiting / ≥20s slow）与并行度芯片（只读）。

### FR-5 意图路由（精简版 3 类）
- FR-5.1 首轮（`user_turns ≤ 1`）→ `new_topic`，不经续聊路由器。
- FR-5.2 第 2 轮起含 URL/上传链接 → `append_urls`。
- FR-5.3 其余一律 → `query_corpus`（依据已生成综述与语料回答）。
- FR-5.4 已有语料时即便 LLM 误判换题，也按 `query_corpus` 处理；换题需新开会话。
- FR-5.5 澄清门：`understand` 输出 `confidence < 0.6` 进入 `clarify`，最多 3 轮，超限带提示强制进入检索。零命中且无上传 URL → 报错结束。

### FR-6 Artifact 面板
- FR-6.1 四 Tab：**大纲 / 综述 / 矩阵 / 文献**。
- FR-6.2 综述 Tab 含版本下拉（latest / v1 / v2…）+ 导出按钮。
- FR-6.3 文献 Tab 取 `GET /api/sessions/{id}/library`，可按子主题标签筛选、复制 APA。
- FR-6.4 存在综述产物即认为有面板；未打开时轻推动画 + 完成栏 CTA 引导。

### FR-7 文献库（`/library`）
- FR-7.1 两栏布局；头部"刷新元数据"（并行 1–12，默认 4）。
- FR-7.2 列表：搜索（多字段子串）、筛选芯片（全部/有全文/失败/收藏/本会话）、标签过滤（多选 OR）、结果计数；排序失败优先后按 `display_index`。
- FR-7.3 文献卡片：序号+标题、作者行、出处/年份/计量、标签、引用复制（仅 APA）、收藏、删除、徽标行。
- FR-7.4 详情面板 Tab：摘要（始终）/ 全文（有全文）/ 元数据（始终）/ 综述（有 provenance）/ PDF（有 PDF）。
- FR-7.5 DOI 内联编辑（保存可 `refresh_crossref`）、标签编辑（≤20 个，每个 ≤48 字符）。

### FR-8 引用抽取与入库
- FR-8.1 出版商识别（arxiv/dblp/acm/ieee/semantic_scholar/generic；elsevier/researchgate/google_scholar 为屏蔽源）。
- FR-8.2 元数据分层合并（出版商 API > HTML meta > 正文）。
- FR-8.3 成功判定：有效标题 +（作者或年份）+ 学术信号；不足不写半条，正文标注「待核实」。
- FR-8.4 OpenAlex + Crossref 富化（被引/他引/补全）。
- FR-8.5 按 canonical key（DOI 优先否则 URL）去重 upsert，分配 `display_index`，生成 APA，写 provenance，同步导出。

### FR-9 设置（管理员）
- FR-9.1 凭据：tavily/brave/semantic_scholar/jina/llm:*（openai/minimax/alibaba/zhipu/ollama），掩码存储 + 测试 + 保存。
- FR-9.2 实例：名称 + 模型 + 绑定 LLM 凭据；测试做绑定校验。
- FR-9.3 能力-检索与抓取：web_search / web_fetch 参数与凭据绑定 + 连通测试面板。
- FR-9.4 能力-编排与综述（Prompts）：各阶段模板 + max_tokens + 实例绑定。
- FR-9.5 存储：Turso URL/Token 配置（可选）。
- FR-9.6 概览页：存储就绪度 + 5 能力就绪度。
- FR-9.7 配置优先级：系统配置 > `.env` > `deploy.defaults.json`。

## 5. 非功能需求（NFR）

| 编号 | 需求 |
|------|------|
| NFR-1 | 无强制数据库：默认本地文件（JSON/JSONL/Markdown）+ FileLock 可运行；Turso 可选 |
| NFR-2 | 并发安全：共享文件写入加锁 + 原子替换 |
| NFR-3 | 流式优先：SSE 真流式透传；前端 rAF 批渲染 + 120s 看门狗 |
| NFR-4 | 秘钥安全：API 返回一律掩码，明文仅存服务端配置文件/env |
| NFR-5 | 成本可见：并行度等放大成本设置不隐藏 |
| NFR-6 | 国际化：界面中文为主；学术检索式英文（剥离中日韩字符） |
| NFR-7 | 限流契约：arXiv 1req/3s、PMC ~3req/s、S2 3.5s/1.1s、每学术源单并发、429 退避 |
| NFR-8 | 代码质量：PEP8 + flake8 通过；后端核心逻辑单测覆盖率 ≥ 80% |
| NFR-9 | Python 3.14；前端 Node LTS；部署 Docker/venv |

## 6. 验收基线（详见 10 文档）

精简版验收清单在原 FRS 第 7 章基础上删除"6 类意图""ACM 切换""版本 a/b""revise"相关项，新增"3 意图路由正确""append_urls 触发整篇重写""query_corpus 以已生成综述为首要依据"。

## 7. 术语表

| 术语 | 含义 |
|------|------|
| Task | 一次后端执行单元，对应一条用户消息的完整流程，产出 SSE 流 |
| Turn / 回合 | 一轮用户↔助手交互；助手回合含执行轨迹（流程卡片）与产物 |
| Artifact | 右侧面板产物：综述 markdown / 矩阵 markdown / 大纲 json / 文献列表 |
| Corpus / 语料 | 本会话收录的文献集合（`corpus.json`，含 `paper_index`） |
| Intent / 意图 | 路由分类结果（3 类之一） |
| Clarification gate / 澄清门 | 置信度不足或零命中时暂停并向用户提问 |
| Capability / 能力 | 管理员可配置的能力单元（review_main/orchestrator/web_search/web_fetch/literature_source） |
| Instance / 实例 | LLM 实例 = 名称 + 模型 + 绑定凭据 |
| Meso 信封 | SSE 事件统一信封格式（v1.0） |
