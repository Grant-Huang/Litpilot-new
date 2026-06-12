# 06 · 工具复用与入库层详设

> 对应 plan todo `tools`。本文说明如何把 `docs/ref` 的工具/技能代码落地到 `backend/app/`，以及必须自写的文献库入库层（`app/library/*`）、提示词注册（`prompt_registry`/`prompt_settings`）。

---

## 1. ref 工具落地方式

将 `docs/ref/tools/**` 整体复制到 `backend/app/agents/tools/`，`docs/ref/skills/**` 复制到 `backend/app/skills/`，`docs/ref/schemas/**` 复制到 `backend/app/schemas/`。**保持 import 路径 `app.agents.tools.*` / `app.skills.*` / `app.schemas.*` 不变**，因此 backend 包根必须是 `app`。

落地清单（只读参考，不改逻辑）：

```
app/agents/tools/web_providers.py
app/agents/tools/cached_tools.py
app/agents/tools/search_hits.py
app/agents/tools/web_search_domains.py
app/agents/tools/metadata_fetch.py
app/agents/tools/source_resolve.py
app/agents/tools/pdf_text.py
app/agents/tools/providers/{__init__,tavily,brave,openalex,native_search,native_fetch,jina,multi_academic}.py
app/agents/tools/providers/academic/{__init__,_hit,arxiv,crossref,pubmed,semantic_scholar,source_gate,api_pacing,ss_rate_limit,query_sanitize}.py
app/skills/{__init__,citation_extractor,citation_meta,paper_attributes}.py
app/schemas/{paper_record,corpus_paper,literature_outline}.py
```

> 注意：`docs/ref/skills/citation_extractor.py` 存在空行较多的格式，落地后用 flake8 校验并最小修正（仅格式，不改逻辑）。

## 2. 必须自写以满足 ref 依赖的模块

### 2.1 `app/library/canonical.py`

```python
def normalize_url(url: str) -> str:
    """去 fragment/utm、统一 scheme/host 小写、去末尾斜杠。"""

def canonical_key(*, url: str | None = None, doi: str | None = None) -> str:
    """DOI 优先：'doi:10.1145/x'（小写）；否则 'url:<normalize_url>'。空则返回 ''。"""
```
- 被 `schemas/paper_record.make_paper_id` 与入库去重共用。

### 2.2 `app/library/store.py`

```python
class LibraryStore:
    """读写 refs/library.json（FileLock + 原子写）。"""
    def load() -> dict                      # {version,next_display_index,items,keys}
    def save(data) -> None
    def get_by_key(canonical_key) -> dict | None
    def get(item_id) -> dict | None
    def put(item: dict) -> dict             # 写入并维护 keys 索引
    def all_items() -> list[dict]           # 按 display_index 升序
    def delete(item_id) -> bool             # 连带 sources/{id}.md
    def alloc_display_index() -> int        # next_display_index++ 持久化
```

### 2.3 `app/library/upsert_citation.py`

```python
def upsert_from_citation(
    rec: "CitationRecord",
    *,
    lib: LibraryStore | None = None,
    citation_format: str = "apa",
    session_id: str = "",
    session_title: str = "",
    enrich_patch: dict | None = None,
) -> dict | None:
    """
    1. 计算 canonical_key（doi 优先否则 url）。
    2. 命中 keys → 合并（更新缺失字段、合并 provenance（≤20）、计 merged）。
       未命中 → 新建 item，alloc display_index。
    3. 合入 enrich_patch（citation_count/references_count/references_preview/venue/year…）。
    4. 生成 citations.apa = rec.to_apa(display_index)（[n] 占位用 display_index）。
    5. 写 availability（fetch_status/cite_status）、provenance（session_id/role/turn_at/session_title）。
    6. lib.put(item) 持久化。返回 item dict。
    """
```
- **精简版**：`citations` 仅写 `apa`；不生成 `acm`。
- provenance 去重合并上限约 20 条。

### 2.4 `app/library/metadata_enrich.py`

```python
async def enrich_records_parallel(records: list, *, parallel: int) -> list[dict]:
    """对每条 CitationRecord：
    - 有 DOI → Crossref 取 citation_count/references_count/references_preview/卷期页。
    - 无 DOI → OpenAlex 按 title+首作者+year 反查 DOI，再 Crossref。
    返回与输入同序的 patch dict 列表（缺失字段留空）。
    遵守限流：复用 metadata_fetch 的节流/退避，semaphore=clamp(parallel,1,12)。"""

async def enrich_one(record) -> dict: ...   # 供 POST /library/items/{id}/enrich
```
- Crossref/OpenAlex 调用复用 `app/agents/tools/metadata_fetch.py` 与 academic providers。

### 2.5 `app/library/from_run.py`

```python
def _sync_exports(lib: LibraryStore) -> None:
    """库变更后同步兼容导出：
    - refs/ref-list.txt：全部 item 的 APA 引用文本（按 display_index）。
    - refs/index.json：旧格式索引（id/display_index/title/url/doi）。"""
```

## 3. 提示词注册与读取

### 3.1 `app/agents/prompt_registry.py`（默认模板常量）

存放 flow-card 文档第六章的全部默认提示词字符串常量：

```python
DEFAULT_UNDERSTANDING_SYSTEM = """你是文献综述助手的过程解说员与检索规划器（Checkpoint A）…"""
DEFAULT_ROUTER_SYSTEM = """你是文献综述助手的路由器…"""                  # 首轮
DEFAULT_INTENT_ROUTER_SYSTEM = """你是文献综述助手的续聊意图路由器…"""    # 3 意图→2 选 1
DEFAULT_ASSESSOR_SYSTEM = """你是学术文献综述助手（首轮 brief 评估）…"""
DEFAULT_CLARIFY_SYSTEM = """你是学术文献综述助手的澄清与推荐器…"""
DEFAULT_SEARCH_REFINER_SYSTEM = """你是学术文献检索专家…"""
DEFAULT_NARRATE_SEARCH_AFTER = """检索后（≤80字）…"""
DEFAULT_NARRATE_FETCH_AFTER = """抓取后（≤40字）…"""
DEFAULT_REVIEW_SYSTEM_PROMPT = """你是学术文献综述助手。仅依据…【参考文献：格式严格遵循 APA 规范】"""
DEFAULT_SECTION_SYSTEM = """你是学术文献综述助手。仅撰写当前章节…引用沿用 APA 编号。"""
DEFAULT_ATTRIBUTE_SYSTEM = """你是学术论文结构化提取器…"""
DEFAULT_SUMMARY_SYSTEM = """你是学术论文网页压缩器…"""
DEFAULT_SUBTOPIC_TAG_SYSTEM = """根据文献标题/摘要与现有子主题列表…"""
DEFAULT_QUERY_CORPUS_SYSTEM = """你是学术文献助手。仅根据【已生成综述】与【多源材料】回答…"""
DEFAULT_MATRIX_SYSTEM = """你是学术文献综述矩阵生成助手…引用编号沿用 [Citations]（APA）…"""
```

> **精简版关键**：所有模板把 `{fmt_label}`/`{citation_format}` 写死为 APA；`query_corpus` 模板含 `[已生成综述]` 为首要依据。

### 3.2 提示词元数据表

```python
PROMPT_META = [
  {"key":"understanding_system_template","label":"理解与规划","group":"orchestrator","hint":"…","max_len":8000,"default_max_tokens":2000,"max_tokens_limit":4000},
  {"key":"intent_router_system_template","label":"意图路由","group":"router","hint":"…","max_len":4000,"default_max_tokens":300,"max_tokens_limit":500},
  {"key":"assessor_system_template","label":"首轮评估","group":"assessor","hint":"…","max_len":6000,"default_max_tokens":720,"max_tokens_limit":6000},
  {"key":"clarify_system_template","label":"澄清推荐","group":"orchestrator","hint":"…","max_len":6000,"default_max_tokens":900,"max_tokens_limit":6000},
  {"key":"search_refiner_system_template","label":"检索消歧","group":"search","hint":"…","max_len":4000,"default_max_tokens":640,"max_tokens_limit":4000},
  {"key":"review_system_prompt_template","label":"综述写作","group":"generation","hint":"…","max_len":12000,"default_max_tokens":3000,"max_tokens_limit":8000},
  {"key":"section_system_template","label":"分章写作","group":"generation","hint":"…","max_len":4096,"default_max_tokens":1200,"max_tokens_limit":4096},
  {"key":"attribute_system_template","label":"结构化抽取","group":"pipeline","hint":"…","max_len":4000,"default_max_tokens":600,"max_tokens_limit":2000},
  {"key":"summary_system_template","label":"网页摘要","group":"pipeline","hint":"…","max_len":4000,"default_max_tokens":600,"max_tokens_limit":2000},
  {"key":"query_corpus_system_template","label":"语料问答","group":"generation","hint":"…","max_len":4000,"default_max_tokens":2048,"max_tokens_limit":4000},
  {"key":"matrix_system_template","label":"矩阵生成","group":"generation","hint":"…","max_len":8000,"default_max_tokens":4096,"max_tokens_limit":8192},
]
```

### 3.3 `app/agents/prompt_settings.py`（运行期读取，含覆盖）

```python
async def get_prompt(key: str) -> str:
    """返回 system.capabilities.json prompts.params[key] 覆盖值；空串则回退 prompt_registry 默认。"""

async def get_prompt_max_tokens(key: str) -> int:
    """返回 params[f'{key}_max_tokens']；缺省取 META.default_max_tokens；clamp 到 [80, max_tokens_limit]。"""

def load_all_prompts() -> dict[str, str]:
    """同步读取全部提示词默认值与覆盖值，返回 {key: text}。
    用于 GET /api/settings/prompts 端点。"""

# 便捷封装（ref paper_attributes 依赖 get_attribute_system_prompt）
async def get_attribute_system_prompt() -> str: return await get_prompt("attribute_system_template")
```

## 4. 典型调用链（引擎将复用，见 07）

```python
# 检索（注意 cached_web_search 首参是 api_key）
data = await cached_web_search(api_key, query, provider="multi_academic",
                               max_results=settings["search_max_results"],
                               include_domains=settings["include_domains"],
                               exclude_domains=settings["exclude_domains"])
hits = apply_literature_hit_filters(data["results"], settings)   # search_hits.py

# 抓取（并行）
text = await cached_web_fetch(url, provider="native",
                              timeout=settings["fetch_timeout_sec"],
                              pdf_extract_backend=settings["pdf_extract_backend"])

# 引用抽取入库（固定 apa）
records = await extract_and_persist_batch(hits, fetch_api_key=settings.get("jina_api_key"),
                                          timeout=settings["fetch_timeout_sec"],
                                          max_items=settings["max_fetch_urls"],
                                          citation_format="apa",
                                          session_id=sid, session_title=title)

# 结构化
jobs = build_extraction_jobs(fetch_results=fr, cite_records=records, paper_index=paper_index)
papers = await extract_attributes_batch(await get_planner_llm(), jobs, parallel=settings["fetch_parallel"])
```

## 5. 限流契约（务必照搬，违反会被封禁）

- arXiv 1 req/3s；PMC ~3 req/s；Semantic Scholar 3.5s(无 key)/1.1s(有 key)；每学术源单并发；429 指数退避带预算上限。
- 这些已在 ref `academic/api_pacing.py`、`ss_rate_limit.py`、`source_gate.py` 内实现，落地后**不要改阈值**。
- 学术查询英文：`query_sanitize` 会剥离中日韩字符，引擎传给 web_search 的 query 必须是英文检索式。

## 6. TDD 要点（本阶段）

| 测试文件 | 覆盖 |
|----------|------|
| `tests/test_canonical.py` | DOI/URL 归一化、canonical_key 去重一致性 |
| `tests/test_library_store.py` | put/get/delete、display_index 分配、keys 索引、原子写 |
| `tests/test_upsert_citation.py` | 新建 vs 命中合并、provenance 去重上限、仅生成 apa |
| `tests/test_metadata_enrich.py` | DOI→Crossref、无 DOI→OpenAlex 反查（respx mock）、并行限流 |
| `tests/test_prompt_settings.py` | 覆盖优先、max_tokens clamp、默认回退 |
| `tests/test_tools_smoke.py` | mock httpx 下 cached_web_search/cached_web_fetch 走通（验证 ref 落地 import 正常） |

> 工具层联网测试用 respx/responses mock，不真实联网；保留 1 个可选 `@pytest.mark.network` 的端到端冒烟。
