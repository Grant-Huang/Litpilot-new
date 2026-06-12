# 10 · 部署与测试方案

> 对应 plan todo `deploy`。本文定义环境变量、Docker/venv 部署、TDD 策略、覆盖率门槛与验收清单映射。

---

## 1. 环境变量

| 变量 | 作用 | 默认 |
|------|------|------|
| `LITPILOT_DATA_DIR` | 运行期数据目录 | `data` |
| `LITPILOT_CONFIG_DIR` | 配置目录 | `config` |
| `LITPILOT_STORAGE_BACKEND` | `local`/`turso`/`hybrid` | `local` |
| `TURSO_DATABASE_URL` | Turso 连接（可选） | — |
| `TURSO_AUTH_TOKEN` | Turso token（可选） | — |
| `TAVILY_API_KEY` / `BRAVE_API_KEY` / `JINA_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY` | 检索/抓取 key（回退源） | — |
| `OPENAI_API_KEY` 等 | LLM key 回退 | — |
| `LITPILOT_CORS_ORIGINS` | 允许的前端源（逗号分隔） | `http://localhost:3000` |
| `NEXT_PUBLIC_API_BASE` | 前端访问后端基址 | `http://localhost:8000` |

- 优先级：系统配置 json > env > `deploy.defaults.json`（见 05 §1.2）。
- `.env` 由 `.gitignore` 排除；提供 `.env.example` 列出变量名（不含值）。

## 2. .gitignore（关键项）

```
.env
__pycache__/
*.pyc
.venv/
backend/data/
backend/config/system.*.json     # 含敏感项
node_modules/
.next/
*.log
.tmp/
```
- `deploy.defaults.json`（非敏感）随仓库；`system.*.json`（含 secret）不入库。

## 3. 本地开发（venv）

```bash
# 后端
cd backend
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev          # http://localhost:3000
```

## 4. 依赖（`backend/requirements.txt`）

```
fastapi
uvicorn[standard]
httpx
filelock
pymupdf
pymupdf4llm
pypdf
python-multipart
pydantic
# 开发
pytest
pytest-asyncio
respx
flake8
```
> pymupdf4llm 基于 PyMuPDF（Artifex），商用需许可；可仅用 pypdf 规避（设置 `pdf_extract_backend=pypdf`）。

## 5. Docker

`backend/Dockerfile`：

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV LITPILOT_DATA_DIR=/data LITPILOT_CONFIG_DIR=/config
VOLUME ["/data", "/config"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`docker-compose.yml`（后端 + 前端）：

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./.data:/data", "./.config:/config"]
    env_file: [.env]
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_BASE: http://localhost:8000
    depends_on: [backend]
```

- SSE 经反代时务必关闭缓冲（Nginx：`proxy_buffering off; proxy_cache off;`，配合后端 `X-Accel-Buffering: no`）。

## 6. TDD 策略

### 6.1 原则（遵循用户 TDD 规则）
- 初始阶段允许编写/修改测试；进入冻结后保持断言目标与业务需求不变，仅修语法/拼写。
- 始终改业务代码以满足测试（如方法名不一致改业务代码而非测试）。
- 覆盖率 < 80% 继续补用例。

### 6.2 后端测试金字塔
- **单元**：config/storage/llm（05）、library/tools（06）、router/clarification/content_pipeline（07）、task/sse（08）。
- **集成**：FastAPI `TestClient` 跑通端点（sessions/tasks/library/settings），引擎用 fake LLM + fake 工具。
- **离线优先**：所有外部 HTTP 用 respx mock；保留少量 `@pytest.mark.network` 可选真实冒烟。

### 6.3 覆盖率
- 目标：后端核心模块（`app/agents`、`app/library`、`app/storage`、`app/config`、`app/tasks`）行覆盖 ≥ 80%。
- 命令：`pytest --cov=app --cov-report=term-missing --cov-fail-under=80`。

### 6.4 Lint
- `flake8 app tests`（配置见 `setup.cfg`：max-line-length=100，排除 ref 落地文件的既有风格告警最小修正）。

## 7. 验收清单映射（精简版）

| 验收项 | 关联文档 | 验证方式 |
|--------|----------|----------|
| 四列布局 + 响应式宽度 + Artifact 收窄 | 09 | 手测 + 组件测试 |
| 会话 CRUD + 置顶 + 激活恢复 | 03/09 | 集成测试 + 手测 |
| SSE 流式 + 流程卡片(12 类) + 日志展开 + 检索树 + 完成栏 CTA | 04/08/09 | 集成 + e2e |
| Composer：多行/回车/链接上传(首轮禁用)/停止/静默提示/并行芯片 | 09 | 单测 + 手测 |
| **意图路由 3 类** + 计划确认门 + 澄清卡 | 07 | 单测 `test_router`/`test_clarification` |
| Artifact 四 Tab + 综述版本下拉 + 导出 | 09 | 手测 |
| 文献库两栏 + 搜索/筛选/标签 + 徽标 + 详情五 Tab + DOI/标签编辑 + 刷新 + **仅 APA 复制** | 03/09 | 集成 + 手测 |
| 引用抽取流水线（出版商识别/屏蔽源/成功判定/富化/去重/provenance） | 06 | 单测 `test_upsert_citation`/`test_metadata_enrich` |
| **append_urls 触发整篇重写 v(n+1)** | 07 | 单测 `test_append_urls`/`test_generate_version` |
| **query_corpus 以已生成综述为首要依据，不出产物** | 07 | 单测 `test_query_corpus` |
| 设置五页 + 掩码 + 测试 + 优先级合并 | 03/05 | 集成 + 手测 |
| 统一响应 + 原子写 + FileLock + 看门狗 + 掩码安全 | 全部 | 单测 + 代码审查 |

> 相对原 FRS 第 7 章：删除"6 类意图""ACM 切换""版本 a/b""revise"，改为上表加粗的精简版项。

## 8. CI（可选建议）

- GitHub Actions：后端 `flake8` + `pytest --cov-fail-under=80`；前端 `npm run lint` + `vitest run`。
- 不提交 `.env`、`system.*.json`、运行期数据。
