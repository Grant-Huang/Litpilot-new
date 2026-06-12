# 02 · 数据模型与存储 Schema

> 本文定义所有持久化数据结构与磁盘布局。这是开发期**冻结的契约层**：前后端、存储层、引擎均以本文字段为准。复用 ref 已定义的 `LibraryItem`、`LiteratureOutline`、`PaperRecord`、`CorpusPaperRecord`，本文补齐 ref 未定义的 Session / Message / Task / Config，并给出完整磁盘布局。

---

## 1. 磁盘布局总览

```
{DATA_DIR}/                          # 默认 backend/data，env LITPILOT_DATA_DIR 覆盖
├── sessions/
│   └── {session_id}/
│       ├── meta.json                # 会话元数据
│       ├── messages.jsonl           # 消息历史（每行一条）
│       ├── corpus.json              # 本会话语料（含 paper_index）
│       ├── outline.json             # 大纲（多子主题时；LiteratureOutline）
│       ├── review-latest.md         # 最新综述
│       ├── review-v1.md, review-v2.md … # 版本化综述
│       └── matrix-latest.md         # 最新文献矩阵
├── refs/
│   ├── library.json                 # 全局文献库主文件（FileLock）
│   ├── ref-list.txt                 # 兼容导出（全部 APA 引用文本）
│   └── index.json                   # 兼容旧格式索引
├── sources/
│   └── {item_id}.md                 # 文献全文 markdown
└── pdfs/
    └── {filename}                   # PDF 文件

{CONFIG_DIR}/                        # 默认 backend/config，env LITPILOT_CONFIG_DIR 覆盖
├── system.credentials.json
├── system.instances.json
├── system.capabilities.json
├── system.storage.json
├── personal.preferences.json
└── deploy.defaults.json             # 非敏感部署默认（随仓库）
```

> `{session_id}`：16 位 hex（uuid4 取前 16）。`{item_id}`：16 位 hex。

## 2. Session `meta.json`

```jsonc
{
  "id": "a1b2c3d4e5f60718",
  "title": "AI-native 制造运营管理架构综述",   // 首轮自动命名；新建时为空或"新会话"
  "created_at": "2026-06-11T18:00:00Z",       // ISO8601 UTC
  "updated_at": "2026-06-11T18:05:00Z",
  "pinned": false,
  "user_turns": 2,                            // 用户消息计数，用于首轮判定
  "initial_query": "请综述 AI-native MOM …",   // 首条用户消息
  "review_versions": ["v1", "v2"],            // 已产出综述版本，无字母后缀
  "last_intent": "append_urls",               // new_topic|append_urls|query_corpus
  "pending_gate": null,                       // 见 §6 澄清门状态；无门时 null
  "resume_mode": null,                        // null|generate_only（大纲确认后跳检索）
  "outline_mode": "lite"                      // off|lite|full（精简版默认 lite）
}
```

字段约束：
- `title`：8–24 字，禁止「综述/新综述/文献综述」等泛称（由 understand 生成）。
- `user_turns`：每收到一条用户消息 +1；`≤1` 判首轮。
- `review_versions`：仅数字版本字符串列表，单调递增。

## 3. Message `messages.jsonl`

每行一个 JSON 对象（`LitPilotMessage`）：

```jsonc
{
  "id": "m_0001",
  "session_id": "a1b2c3d4e5f60718",
  "role": "user",                    // user|assistant
  "content": "请综述 …",             // 纯文本正文
  "created_at": "2026-06-11T18:00:00Z",
  "extras": {                        // 仅 assistant 回合可能存在
    "delivery": "process",           // chat|process|artifact
    "artifactKind": "review",        // review|matrix|outline|none
    "intent": "new_topic",
    "executionTrace": [ /* WorkflowCard[] 见 §3.1 */ ],
    "turnWorkflow": { /* 聚合统计，见 §3.2 */ },
    "review_version": "v1"           // 本回合产出的综述版本（如有）
  }
}
```

### 3.1 WorkflowCard（执行轨迹元素 — 简化版）

前端实际使用的简化结构（stage + state + logs）：

```jsonc
{
  "stage": "search",               // understand|brief|search|fetch|cite|attributes|outline|generate|matrix|corpus_qa|clarify|manage
  "state": "done",                 // pending|running|done|error
  "logs": [                        // 可展开的日志行列表
    "逻辑检索 · arXiv（21 篇）",
    "OpenAlex 返回 18 条命中"
  ]
}
```

> **变更说明**：原设计含 `type/title/summary/steps/tree` 等复杂嵌套结构，实现中简化为 `stage/state/logs` 三字段。前端 WorkflowCard 组件据此渲染：阶段图标 + 状态标识 + 日志行展开/折叠。后端 SSE `stage` 事件通过 `sse.ts` 的 `updateTrace` 函数映射中文阶段名为 stage 标识。

### 3.2 turnWorkflow（回合完成栏数据）

```jsonc
{
  "headline": "检索 · 纳入 47 篇 · 获取 42 篇 · 综述已生成",
  "weak_subtopics": [ {"title": "信任机制", "count": 3} ],
  "has_review": true,
  "has_matrix": true
}
```

### 3.3 检索进度树节点

```jsonc
{
  "subtopics": [
    {
      "id": "st1", "title": "AI-native MOM 架构",
      "state": "done", "pass_done": 5, "pass_total": 5,
      "sources": [
        {"source": "openalex", "label": "OpenAlex", "hits": 18, "state": "done"},
        {"source": "arxiv", "label": "arXiv", "hits": 0, "state": "error"}
      ],
      "filter": {"kept": 12, "rejected": 6}      // LLM 二段过滤后
    }
  ]
}
```

## 4. Corpus `corpus.json`

```jsonc
{
  "version": 2,
  "session_id": "a1b2c3d4e5f60718",
  "papers": [ /* CorpusPaperRecord（v3 schema，见 ref/schemas/corpus_paper.py） */ ],
  "paper_index": [ /* PaperRecord（见 ref/schemas/paper_record.py） */ ],
  "search_aspects": [ /* understand 阶段产出的检索规划，见 §7.1 */ ],
  "updated_at": "2026-06-11T18:05:00Z"
}
```

- `papers`：`CorpusPaperRecord.to_dict()` 列表（url/title/library_id/subtopic_tags/fetch_status/has_pdf/enrich_lite/cite_in_review）。
- `paper_index`：`PaperRecord.to_dict()` 列表（paper_id/url/title/library_id/bib_key/attri）。`attri` 含 problem/method/datasets/findings/limitations/keywords。
- 多轮续聊复用语料；`append_urls` 增量合并（`merge_corpus_papers` / `merge_paper_index`）。

## 5. Outline `outline.json`

直接采用 ref `LiteratureOutline.to_dict()`：

```jsonc
{
  "version": 1,
  "topic": "AI-native 制造运营管理",
  "research_questions": ["RQ1 …", "RQ2 …"],
  "sub_topics": [
    {"id": "st1", "title": "架构范式", "description": "…", "search_query": "…",
     "source_queries": {"arxiv": "…", "semantic_scholar": "…"}, "exclude_terms": ["…"]}
  ],
  "sections": [
    {"id": "sec1", "number": "三", "title": "主要研究工作对比", "desc": "…",
     "sub_topic_id": "st1", "mounted_paper_ids": ["<paper_id>"], "mount_hints": []}
  ],
  "status": "draft"                  // draft|confirmed
}
```

## 6. 澄清门状态 `meta.pending_gate`

```jsonc
{
  "kind": "outline_confirm",         // first_turn|search_zero|outline_confirm（精简版保留这三类）
  "prompt": "您的大纲已经生成：…",
  "options": ["确认继续撰写综述", "修改大纲并重新生成", "添加/删除子主题"],
  "created_at": "2026-06-11T18:03:00Z"
}
```

解析后清空 `pending_gate`，根据 kind 设置 `resume_mode`（outline_confirm 通过 → `generate_only`）。

## 7. understand 产物 schema

### 7.1 search_aspects（检索规划，存 corpus.json）

```jsonc
[
  {
    "aspect_id": 1,
    "aspect_label": "架构范式",
    "core_concepts": ["编排架构", "agent orchestration"],
    "arxiv_query": "ai-native manufacturing operations management agent orchestration",
    "semantic_scholar_query": "ai native manufacturing operations management platform",
    "openalex_crossref_query": "\"manufacturing operations management\" \"ai-native\" architecture",
    "pubmed_query": "",
    "exclude_terms": ["municipal", "how to write"]
  }
]
```

### 7.2 understand LLM 末行 JSON（引擎解析，不单独落盘）

```jsonc
{
  "narration": "3-5 句中文解说",
  "confidence": 0.85,
  "session_title": "8-24 字标题",
  "search_query": "≤120 字英文检索线索",
  "narration_focus": "…",
  "writing_emphasis": "…",
  "search_aspects": [ /* §7.1 */ ]
}
```

## 8. Task（内存对象，不持久化磁盘）

`TaskManager` 维护内存任务表；进程重启即失效（前端通过会话消息恢复历史）。

```jsonc
{
  "task_id": "t_9f8e7d6c",
  "session_id": "a1b2c3d4e5f60718",
  "message": "用户输入文本",
  "fetch_urls": ["https://…"],       // 可选，append_urls
  "status": "running",               // pending|running|done|error|cancelled
  "created_at": "...",
  "events": [ /* Meso 信封序列，带递增 seq，供 since=N 续传，见 04 文档 */ ],
  "error": null
}
```

## 9. 文献库 `refs/library.json`（复用 FRS LibraryItem）

主文件结构（FileLock 并发安全）：

```jsonc
{
  "version": 1,
  "next_display_index": 48,
  "items": { "<item_id>": { /* LibraryItem，见 FRS §2.5 */ } },
  "keys": { "<canonical_key>": "<item_id>" }
}
```

`LibraryItem` 关键字段（精简版固定 APA，`citations` 仅需 `apa`）：

```jsonc
{
  "id": "16hex",
  "display_index": 12,
  "canonical_key": "doi:10.1145/xxxxxxx",
  "title": "…", "authors": ["A. Author"], "venue": "…", "year": "2024",
  "url": "https://…", "doi": "10.1145/…", "publisher": "ACM",
  "abstract": "…", "summary_bullets": ["…"],
  "full_text": {"kind": "markdown", "path": "sources/<id>.md", "char_count": 8421, "fetched_at": "…"},
  "citation_count": 31, "references_count": 45,
  "references_preview": [{"title": "…", "year": "2019", "doi": "…"}],
  "availability": {"has_abstract": true, "has_full_text": true, "has_pdf": false,
                   "fetch_status": "ok", "cite_status": "ok"},
  "citations": {"apa": "[n] A. Author (2024). Title. Venue. https://doi.org/…"},
  "provenance": [{"session_id": "…", "role": "assistant", "turn_at": "…",
                  "session_title": "…", "review_ref_index": 3}],
  "tags": ["mom"], "subtopic_tags": ["st1"], "starred": false,
  "enrich_lite": {"method_one_liner": "…", "findings_one_liner": "…", "year": "2024"},
  "created_at": "…", "updated_at": "…"
}
```

去重键（`canonical.py`）：`canonical_key(doi=…)` 优先 `doi:<lower>`；否则 `canonical_key(url=…)` 用归一化 URL。

## 10. 配置文件 Schema（详见 05/06，端点契约见 03）

| 文件 | 顶层结构 |
|------|----------|
| `system.credentials.json` | `{ "items": [ {id, type, name, secret, base_url, group_id, status, last_verified_at, created_at, updated_at} ] }` |
| `system.instances.json` | `{ "items": [ {id, name, provider, credential_id, model_name, default_params, status, created_at, updated_at} ] }` |
| `system.capabilities.json` | `{ "items": [ {capability_id, label, enabled, primary_ref:{kind,id}, params, created_at, updated_at} ] }` |
| `system.storage.json` | `{ database_url, auth_token, tenant_id, updated_at }` |
| `personal.preferences.json` | `{ }`（精简版无 citation_format；保留空对象以兼容） |
| `deploy.defaults.json` | 非敏感默认（provider 默认、并行度默认等） |

> 凭据/存储的 `secret`/`auth_token` 仅存服务端文件；公开响应只返回 `has_secret`/`masked_secret` / `has_auth_token`/`masked_auth_token`（末 4 位）。

## 11. ID 与时间约定

- 所有 ID 用 `secrets.token_hex(8)`（16 hex）或 `uuid4().hex[:16]`。
- 所有时间戳 ISO8601 UTC（`datetime.now(timezone.utc).isoformat()`）。
- `display_index` 单调递增，删除不回收（`next_display_index` 持久化）。
