# 11 · 里程碑与 TDD TodoList

> 本文把 plan 的 7 个开发阶段细化为可执行、避免单步上下文溢出的 TDD 任务序列，并定义里程碑验收。每步遵循"先写测试 → 实现 → 通过 → 更新进度"。

---

## 1. 里程碑

| 里程碑 | 目标 | 完成判据 |
|--------|------|----------|
| M0 | 设计文档冻结 | 本目录 00–11 评审通过，契约层（02/03/04）冻结 |
| M1 | 后端跑通 new_topic | `POST /tasks` + SSE 走完整流水线（fake LLM/工具），产出 review-v1 + 入库 |
| M2 | append_urls + query_corpus | 三意图全通；版本 v(n+1)；query_corpus 不出产物 |
| M3 | 文献库 + 设置 | library 全端点 + settings 五页后端 + 掩码/测试 |
| M4 | 前端联调 | 三大界面与真实后端打通，SSE 可视化 |
| M5 | 部署 + 验收 | Docker 起服、flake8 通过、覆盖率 ≥80%、验收清单回归 |

## 2. 阶段任务拆解（TDD）

### 阶段 1 · 设计文档（plan todo: docs）✅ 当前阶段
- [x] 00 需求汇总
- [x] 01 架构
- [x] 02 数据 schema
- [x] 03 API 契约
- [x] 04 SSE 事件
- [x] 05 配置/存储/LLM
- [x] 06 工具/入库
- [x] 07 编排引擎
- [x] 08 Task/SSE 流式
- [x] 09 前端
- [x] 10 部署/测试
- [x] 11 里程碑/todolist

### 阶段 2 · 后端骨架与底座（plan todo: skeleton）
1. 初始化 `backend/`：`requirements.txt`、`pyproject/setup.cfg`、`app/main.py`、包结构。
2. `config/paths.py` + 测试。
3. `config/system_config.py`（原子写/掩码/CRUD/冲突）+ 测试。
4. `config/personal_config.py`（空实现）+ 测试。
5. `agents/ttl_cache.py` + 测试。
6. `agents/runtime_settings.py`（三层合并）+ 测试。
7. `agents/agent_settings.py`（get_* getter）+ 测试。
8. `storage/file_store.py`（会话/消息/corpus/review 版本）+ 测试。
9. `llm/base.py` + `llm/openai_compat.py` + `llm/factory.py`（respx mock）+ 测试。

### 阶段 3 · 工具落地与入库层（plan todo: tools）
1. 复制 ref `tools/**`、`skills/**`、`schemas/**` 到 `app/`，flake8 最小修正。
2. `library/canonical.py` + 测试。
3. `library/store.py` + 测试。
4. `library/upsert_citation.py`（仅 APA）+ 测试。
5. `library/metadata_enrich.py`（Crossref/OpenAlex，respx）+ 测试。
6. `library/from_run.py`（导出同步）+ 测试。
7. `agents/prompt_registry.py` + `prompt_settings.py` + 测试。
8. `test_tools_smoke.py`：mock 下验证 cached_web_search/cached_web_fetch import 与调用链。

### 阶段 4 · 编排引擎（plan todo: engine）
1. `literature_router.py`（3 意图规则 + LLM 兜底）+ 测试。
2. `content_pipeline.py`（材料分栏）+ 测试。
3. `literature_clarification.py`（三门）+ 测试。
4. `literature_turn_pipeline.py`（检索→抓取→引用→结构化→大纲）+ 测试（fake 工具）。
5. `literature_turn_generate.py`（综述/矩阵/问答）+ 测试。
6. `literature_turn_finalize.py`（落盘/库/消息）+ 测试。
7. `literature_turn.py`（编排入口 run_turn + emit）+ 测试（new_topic 全流程事件序列）。
8. `test_append_urls.py` / `test_query_corpus.py` / `test_generate_version.py`。

### 阶段 5 · Task 与 SSE（plan todo: streaming）
1. `tasks/manager.py`（TaskRecord/emit/run/cancel）+ 测试。
2. `tasks/sse.py`（信封/续传/心跳）+ 测试。
3. `api/tasks.py`（4 端点，首轮 fetch_urls 400）+ 测试（TestClient）。
4. `api/sessions.py`（CRUD + 产物只读）+ 测试。
5. `api/library.py` + `api/settings.py`（含 web_search/web_fetch/credential 测试端点）+ 测试。
6. `app/main.py` 路由挂载 + CORS。

### 阶段 6 · 前端（plan todo: frontend）
1. 脚手架 + brand tokens + 布局 + 重定向。
2. `lib/api.ts`/`lib/sse.ts`/`lib/stream-reducer.ts`/`lib/types.ts`/`lib/store.ts` + 单测。
3. `/chat`：会话列表 + 消息区 + AssistantTurn/WorkflowCard/LogRow/SearchProgressView/TurnCompletionBar。
4. Composer（多行/链接上传/停止/静默/并行芯片）。
5. ArtifactPanel 四 Tab（Outline/Review/Matrix/Literature）。
6. `/library`（列表 + 筛选 + 详情五 Tab + DOI/标签编辑 + 刷新元数据）。
7. `/settings`（个人只读 + 管理员五页 + 掩码/测试/dirty 守卫）。

### 阶段 7 · 部署与验收（plan todo: deploy）
1. `.env.example`、`.gitignore`、`deploy.defaults.json`。
2. `backend/Dockerfile` + `frontend/Dockerfile` + `docker-compose.yml`。
3. flake8 全通过；`pytest --cov-fail-under=80` 达标。
4. 按 10 §7 验收清单逐项回归（含 3 意图、v(n+1)、仅 APA）。
5. README（运行/部署说明）。

## 3. 防上下文溢出约定

- 每个阶段内的子任务单独提交一次（一个模块 + 其测试为一个工作单元）。
- 每完成一个工作单元：跑该模块测试 → flake8 → 更新本文勾选 → 经用户确认再进入下一步。
- ref 落地文件只读不重写，避免大段无意义 diff。

## 4. 风险与对策

| 风险 | 对策 |
|------|------|
| ref 工具隐含依赖未覆盖 | 阶段 3 先跑 `test_tools_smoke` 暴露 ImportError |
| 学术源限流被封 | 严格照搬 ref 节流，测试用 mock，不真实压测 |
| SSE 代理缓冲导致非真流式 | 后端 `X-Accel-Buffering: no` + 文档化反代配置 |
| LLM provider 差异 | 统一 OpenAI 兼容层，差异点（minimax group_id）在 factory 处理 |
| 覆盖率不足 | 引擎用 fake LLM/工具做确定性事件序列断言，便于覆盖分支 |
