# LitPilot 精简版 — 详细设计文档索引

> 本目录是 **LitPilot 精简版** 从零复制开发的完整设计文档集。文档面向开发团队，按"需求 → 架构 → 数据 → 接口 → 子系统详设 → 前端 → 部署测试 → 里程碑"分层组织，可逐篇作为对应开发阶段的实现依据。
>
> 范围冻结：**3 类意图（`new_topic` / `append_urls` / `query_corpus`）、引用格式仅 APA、版本规则 v(n+1) 无字母后缀**。技术栈：前端 Next.js + 后端 FastAPI（Python 3.14）+ 本地文件存储（可选 Turso），直接复用 `docs/ref` 的工具与技能代码。

## 文档清单

| 编号 | 文档 | 对应开发阶段（plan todo） | 内容 |
|------|------|--------------------------|------|
| 00 | [需求汇总](./00-requirements.md) | docs | 精简版需求、范围冻结、与原 FRS 的差异、术语表 |
| 01 | [总体架构设计](./01-architecture.md) | docs | 分层架构、模块边界、目录结构、技术选型、复用/自写边界 |
| 02 | [数据模型与存储 Schema](./02-data-schema.md) | docs | Session/Message/Corpus/Task/Library/Outline/Config 全字段定义与文件布局 |
| 03 | [REST API 契约](./03-api-contract.md) | docs / streaming | 全部端点的请求/响应体、状态码、错误约定 |
| 04 | [SSE 事件契约（Meso v1.0）](./04-sse-events.md) | docs / streaming | 信封格式、全部 event 与 extension 事件 payload |
| 05 | [配置/存储/LLM 注入层详设](./05-config-storage-llm.md) | skeleton | `agent_settings`、`runtime_settings`、`file_store`、`llm` 客户端 |
| 06 | [工具复用与入库层详设](./06-tools-integration.md) | tools | ref 工具落地、`library.*` 入库层、`prompt_registry`/`ttl_cache` |
| 07 | [编排引擎详设](./07-orchestration-engine.md) | engine | 3 意图路由、流水线、澄清门、content_pipeline、提示词接入 |
| 08 | [Task 与 SSE 流式层详设](./08-task-streaming.md) | streaming | 任务生命周期、SSE 推流、断点续传、看门狗、落盘回读 |
| 09 | [前端设计详设](./09-frontend.md) | frontend | 三大界面、组件清单、状态管理、SSE 消费、矩阵/大纲渲染 |
| 10 | [部署与测试方案](./10-deployment-testing.md) | deploy | Docker/venv、env、TDD 策略、覆盖率、验收清单映射 |
| 11 | [里程碑与 TDD TodoList](./11-milestones-todolist.md) | 全部 | M0–M5 里程碑、分阶段 TDD 任务拆解 |

## 阅读顺序建议

1. 先读 00/01 建立全局认知。
2. 实现后端前精读 02/03/04（契约层，开发期冻结）。
3. 按 05 → 06 → 07 → 08 顺序实现后端。
4. 按 09 实现前端。
5. 按 10/11 落地部署、测试与里程碑验收。

## 关键约定（贯穿所有文档）

- 路径一律相对项目根，使用 `/` 分隔符；代码内禁止硬编码绝对路径，统一 `pathlib.Path`。
- Python 遵循 PEP8 / 4 空格缩进；命名：变量函数 `snake_case`、类 `PascalCase`、常量 `UPPER_CASE`。
- 统一 REST 响应结构 `{ "status": "success|error", "data": {}, "message": "可选" }`（SSE 流除外）。
- 所有共享 JSON 文件写入：原子写（`.tmp` → `FileLock` → 替换）。
- 秘钥永不明文返回前端，仅返回 `has_secret` / `masked_*`。
- 引用格式固定 **APA**；底层工具签名保留 `citation_format` 参数但始终传 `"apa"`。
