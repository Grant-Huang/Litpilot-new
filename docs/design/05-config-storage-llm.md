# 05 · 配置 / 存储 / LLM 注入层详设

> 对应 plan todo `skeleton`。本文给出后端骨架最底层的三大支撑：配置注入层（`agent_settings` + `runtime_settings` + `config`）、文件存储层（`file_store`）、LLM 客户端（`llm`）。这是 ref 工具能跑起来的前提（ref 反向依赖见 01 §4）。

---

## 1. 配置目录与优先级

### 1.1 路径解析 `app/config/paths.py`

```python
from pathlib import Path
import os

def data_dir() -> Path:
    return Path(os.environ.get("LITPILOT_DATA_DIR", "data")).resolve()

def config_dir() -> Path:
    return Path(os.environ.get("LITPILOT_CONFIG_DIR", "config")).resolve()
```
- 禁止硬编码绝对路径；目录不存在时首次写入前 `mkdir(parents=True, exist_ok=True)`。

### 1.2 优先级（关键）

```
系统配置(system.*.json) > .env 环境变量 > deploy.defaults.json
```
- 秘钥若系统配置缺省，回退 `.env`：`TAVILY_API_KEY`、`BRAVE_API_KEY`、`JINA_API_KEY`、`SEMANTIC_SCHOLAR_API_KEY`、`OPENAI_API_KEY` 等。
- `runtime_settings.build_runtime_settings()` 合并三层为单一扁平 dict，供 agents 与工具读取。

## 2. 系统配置存储 `app/config/system_config.py`

### 2.1 原子写

```python
def atomic_write_json(path: Path, data: dict) -> None:
    from filelock import FileLock
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(path) + ".lock")
    with lock:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
```

### 2.2 掩码

```python
def mask_secret(secret: str) -> str:
    s = secret or ""
    return f"··· {s[-4:]}" if len(s) >= 4 else ("····" if s else "")
```
- 公开响应只返回 `has_secret`（bool）+ `masked_secret`；明文绝不出后端。

### 2.3 CRUD 接口（供 settings 路由调用）

```python
class SystemConfig:
    def list_credentials() -> list[dict]      # 掩码后
    def get_credential(id) -> dict | None     # 内部含明文，仅服务端用
    def create_credential(payload) -> dict
    def update_credential(id, payload) -> dict # secret 空串=清除→status unknown
    def delete_credential(id)                  # 被实例引用 raise Conflict
    # instances / capabilities / storage 同构
```

冲突校验：删除凭据前扫描 `system.instances.json` 是否引用；删除实例前扫描 `system.capabilities.json` 的 `primary_ref`。

## 3. 个人偏好 `app/config/personal_config.py`

精简版无字段。保留：

```python
def get_preferences() -> dict: return {}          # 始终空
def put_preferences(payload: dict) -> dict: return {}
```
- 引用格式固定 APA，不读个人设置；`citation_format` 在全系统硬编码 `"apa"`。

## 4. 运行时配置 `app/agents/runtime_settings.py`

```python
async def build_runtime_settings() -> dict:
    """合并 system + personal + env + deploy.defaults 为扁平 dict。"""
    # 1. 读 deploy.defaults.json（最低优先）
    # 2. 覆盖 env 中的 provider/并行度/key
    # 3. 覆盖 system.capabilities.json 的 params（web_search/web_fetch/prompts）
    # 4. 解析 capability.primary_ref → instance → credential，得到 LLM 配置
    # 返回示例见 §4.1
```

### 4.1 运行时扁平 dict 关键键

```jsonc
{
  "web_search_provider": "multi_academic",
  "search_max_results": 20, "search_retry_count": 3, "search_depth": "advanced",
  "include_domains": ["arxiv.org", …], "exclude_domains": [],
  "enforce_domain_filter": true, "enable_junk_filter": true,
  "web_fetch_provider": "native", "pdf_extract_backend": "pymupdf4llm",
  "max_fetch_urls": 5, "fetch_parallel": 3, "fetch_timeout_sec": 45,
  "fetch_retry_count": 0, "max_source_chars": 14000,
  "tavily_api_key": "…", "brave_api_key": "…", "jina_api_key": "…", "s2_api_key": "…",
  "review_main": { "provider":"openai","base_url":"…","api_key":"…","model":"deepseek-v4","max_tokens":3000 },
  "orchestrator": { … },               // 缺省回退 review_main
  "prompt_overrides": { "<key>": "模板", "<key>_max_tokens": 280, "<group>_instance_id": "…" }
}
```

## 5. agent_settings.py（工具所需 getter）

ref 工具用 `async` getter 读取配置。实现为对 `build_runtime_settings()` 的薄封装（可加进程内缓存，TTL 几秒）：

```python
# app/agents/agent_settings.py
async def get_web_search_provider() -> str: ...      # 默认 multi_academic
async def get_web_fetch_provider() -> str: ...       # 默认 native
async def get_pdf_extract_backend() -> str: ...      # 默认 pymupdf4llm
async def get_s2_api_key() -> str: ...               # 可空
async def get_jina_reader_api_key() -> str: ...      # 可空
async def get_fetch_parallel() -> int: ...           # 默认 3，clamp 1..8
# 综述/编排 LLM 配置
async def get_review_llm_config() -> dict: ...
async def get_orchestrator_llm_config() -> dict: ... # 回退 review_main
```

> 这些 getter 的名字与返回必须与 ref 调用一致（见 01 §4），否则复用工具会 ImportError。

## 6. 文件存储 `app/storage/file_store.py`

### 6.1 会话存储 API

```python
class FileStore:
    def list_sessions() -> list[dict]
    def create_session(title="") -> dict
    def get_meta(session_id) -> dict | None
    def update_meta(session_id, **patch) -> dict      # 原子写 meta.json
    def delete_session(session_id) -> None

    def read_messages(session_id) -> list[dict]        # 解析 messages.jsonl
    def append_message(session_id, msg: dict) -> dict  # 追加一行（带锁）

    def read_corpus(session_id) -> dict
    def write_corpus(session_id, corpus: dict) -> None

    def read_outline(session_id) -> dict | None
    def write_outline(session_id, outline: dict) -> None

    def read_review(session_id, version="latest") -> str
    def write_review(session_id, markdown: str) -> str # 落 review-vN.md + review-latest.md，返回版本号
    def list_review_versions(session_id) -> list[str]

    def read_matrix(session_id) -> str
    def write_matrix(session_id, markdown: str) -> None

    # 兼容导出（citation_extractor 依赖）
    def read_ref_list() -> str                         # refs/ref-list.txt
    def write_ref_list(text: str) -> None

def get_store() -> FileStore: ...                      # 单例
```

### 6.2 版本化综述写入逻辑

```python
def write_review(self, session_id, markdown):
    versions = self.list_review_versions(session_id)   # ["v1","v2"]
    n = max((int(v[1:]) for v in versions), default=0) + 1
    version = f"v{n}"
    self._write(f"review-{version}.md", markdown)
    self._write("review-latest.md", markdown)
    self.update_meta(session_id, review_versions=versions + [version])
    return version
```
- **精简版无字母后缀**，纯 `v(n+1)` 递增。

### 6.3 jsonl 追加（并发安全）

```python
def append_message(self, session_id, msg):
    path = self._session_path(session_id) / "messages.jsonl"
    with FileLock(str(path) + ".lock"):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    return msg
```

## 7. TTL 缓存 `app/agents/ttl_cache.py`

ref `cached_tools.py` 依赖：

```python
class TTLCache:
    def __init__(self, ttl_sec: float, maxsize: int = 512): ...
    def get(self, key) -> Any | None      # 过期返回 None
    def set(self, key, value) -> None

search_cache = TTLCache(ttl_sec=900)      # 15 min
fetch_cache = TTLCache(ttl_sec=3600)      # 60 min

def normalize_cache_key(provider: str, key: str, extra: dict | None = None) -> str:
    blob = json.dumps({"p": provider, "k": key, "e": extra or {}},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()
```

## 8. LLM 客户端 `app/llm/`

### 8.1 抽象 `base.py`

```python
@dataclass
class LLMMessage:
    role: str          # system|user|assistant
    content: str

@dataclass
class LLMResponse:
    content: str
    finish_reason: str = "stop"
    usage: dict | None = None

class LLMClient(Protocol):
    async def chat(self, messages: list[LLMMessage], *, system: str = "",
                   max_tokens: int = 1024, temperature: float = 0.3) -> LLMResponse: ...
    async def stream(self, messages: list[LLMMessage], *, system: str = "",
                     max_tokens: int = 1024, temperature: float = 0.3) -> AsyncIterator[str]: ...
```

### 8.2 OpenAI 兼容实现 `openai_compat.py`

- 用 httpx 调 `{base_url}/chat/completions`；支持 stream（SSE）。
- 覆盖 provider：openai / zhipu / alibaba（Qwen）/ minimax / ollama —— 均走 OpenAI 兼容协议（minimax 需 `group_id` 时拼到 URL/header）。
- 失败抛 `LLMError`；上层捕获后走规则兜底。

### 8.3 工厂 `factory.py`

```python
async def get_review_llm() -> LLMClient:
    cfg = await get_review_llm_config()
    return build_client(cfg)

async def get_planner_llm() -> LLMClient:
    cfg = await get_orchestrator_llm_config()   # 缺省回退 review_main
    return build_client(cfg)
```

## 9. TDD 要点（本阶段）

| 测试文件 | 覆盖 |
|----------|------|
| `tests/test_paths.py` | env 覆盖、默认目录、相对路径 |
| `tests/test_system_config.py` | 原子写、掩码、CRUD、删除冲突 409 |
| `tests/test_file_store.py` | 会话 CRUD、jsonl 追加、review 版本递增（v1→v2 无字母）、corpus 读写 |
| `tests/test_ttl_cache.py` | 命中/过期/容量淘汰、key 归一化稳定 |
| `tests/test_runtime_settings.py` | 三层优先级合并、primary_ref 解析、orchestrator 回退 review_main |
| `tests/test_llm_factory.py` | 配置 → 客户端构建；chat/stream mock（respx）|

> 测试用临时目录（pytest `tmp_path`）注入 `LITPILOT_DATA_DIR`/`LITPILOT_CONFIG_DIR`，避免污染。
