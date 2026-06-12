"""Literature turn pipeline — search / fetch / cite / corpus / outline phases.

Each phase is an independent async function that takes hits/results and emits
events. Composed by literature_turn._run_new_topic / _run_append_urls.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any
from urllib.parse import urlparse

from app.agents.tools.cached_tools import cached_web_search, cached_web_fetch
from app.skills.citation_extractor import extract_and_persist_batch

_log = logging.getLogger(__name__)


# ── Search ───────────────────────────────────────────────────

async def run_search_phase(
    *,
    queries: list[str],
    emit: Any,
    api_key: str,
    max_results: int = 8,
) -> list[dict[str, str]]:
    """Execute search queries, emit tool events, return merged hits."""
    all_hits: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for query in queries:
        await emit.tool_call("web_search", {"query": query})
        try:
            data = await cached_web_search(
                api_key=api_key,
                query=query,
                max_results=max_results,
            )
            results = data.get("results", [])
            count = 0
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_hits.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "snippet": r.get("snippet", ""),
                        "source": r.get("source", ""),
                    })
                    count += 1
            await emit.tool_result("web_search", f"Found {count} results")
        except Exception as e:
            _log.warning("Search failed for %s: %s", query[:50], e)
            await emit.tool_result("web_search", f"Search error: {e}")

    return all_hits


# ── Fetch ────────────────────────────────────────────────────

async def run_fetch_phase(
    *,
    hits: list[dict[str, str]],
    emit: Any,
    api_key: str | None = None,
    timeout: float = 60.0,
) -> list[dict[str, str]]:
    """Fetch full text for hit URLs in parallel."""
    if not hits:
        return []

    await emit.tool_call("web_fetch", {"urls": [h["url"] for h in hits]})

    sem = asyncio.Semaphore(4)

    async def _fetch_one(hit: dict) -> dict[str, str]:
        url = hit["url"]
        async with sem:
            try:
                text = await cached_web_fetch(
                    url, api_key=api_key, timeout=timeout,
                )
                return {"url": url, "text": text or ""}
            except Exception as e:
                _log.warning("Fetch failed for %s: %s", url[:60], e)
                return {"url": url, "text": "", "error": str(e)}

    results = list(await asyncio.gather(*[_fetch_one(h) for h in hits]))
    fetched_count = sum(1 for r in results if r.get("text"))
    await emit.tool_result(
        "web_fetch", f"Fetched {fetched_count}/{len(hits)} pages"
    )
    return results


# ── Cite ─────────────────────────────────────────────────────

async def run_cite_phase(
    *,
    hits: list[dict[str, str]],
    emit: Any,
    session_id: str = "",
    session_title: str = "",
) -> list[Any]:
    """Extract citations and persist to library."""
    if not hits:
        return []

    await emit.tool_call("citation_extract", {
        "count": len(hits),
    })

    try:
        records = await extract_and_persist_batch(
            hits,
            citation_format="apa",
            session_id=session_id,
            session_title=session_title,
        )
        await emit.tool_result(
            "citation_extract",
            f"Extracted {len(records)} citations",
        )
        return records
    except Exception as e:
        _log.exception("Citation extraction failed")
        await emit.tool_result("citation_extract", f"Error: {e}")
        return []


# ── Build corpus ─────────────────────────────────────────────

def build_corpus_papers(
    *,
    hits: list[dict[str, str]],
    fetch_results: list[dict[str, str]],
    citations: list[Any],
    existing_corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge search hits + fetch results into corpus papers."""
    existing = existing_corpus or {"version": 0, "papers": []}
    existing_papers: list[dict] = list(existing.get("papers", []))
    existing_urls = {p.get("url") for p in existing_papers}

    fetch_by_url = {r["url"]: r for r in fetch_results if r.get("url")}

    new_papers: list[dict] = []
    for hit in hits:
        url = hit.get("url", "")
        if not url or url in existing_urls:
            continue
        fetch = fetch_by_url.get(url, {})
        text = fetch.get("text", "")
        error = fetch.get("error")

        pid = _make_paper_id(url)
        paper = {
            "url": url,
            "title": hit.get("title", ""),
            "snippet": hit.get("snippet", ""),
            "source": hit.get("source", ""),
            "paper_id": pid,
            "fetch_status": "fetched" if text else (
                "fetch_failed" if error else "pending"
            ),
            "full_text_length": len(text),
            "subtopic_tags": [],
        }
        new_papers.append(paper)
        existing_urls.add(url)

    all_papers = existing_papers + new_papers
    version = existing.get("version", 0) + (1 if new_papers else 0)

    return {"version": version, "papers": all_papers}


def _make_paper_id(url: str) -> str:
    """Generate a stable paper_id from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    path_hash = hashlib.md5(parsed.path.encode()).hexdigest()[:6]
    return f"{domain}-{path_hash}"


# ── Outline ──────────────────────────────────────────────────

# Standard 5-section outline for APA review
_STANDARD_SECTIONS = [
    {"id": "s1", "title": "研究背景与问题定位",
     "description": "介绍研究领域背景、核心问题与研究意义"},
    {"id": "s2", "title": "理论/概念框架",
     "description": "综述理论基础与关键概念框架"},
    {"id": "s3", "title": "主要研究工作对比",
     "description": "对比分析主要研究成果与方法"},
    {"id": "s4", "title": "研究空白与未来方向",
     "description": "总结研究空白与未来研究方向"},
    {"id": "s5", "title": "参考文献",
     "description": "APA 格式参考文献列表"},
]


def build_outline(
    *,
    papers: list[dict[str, Any]],
    search_aspects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a standard 5-section outline with mounted papers."""
    sections = []
    for tmpl in _STANDARD_SECTIONS:
        section = {
            "id": tmpl["id"],
            "title": tmpl["title"],
            "description": tmpl["description"],
            "mounted_paper_ids": [],
        }
        sections.append(section)

    # Mount all papers to section 3 (comparison) and s1 (background)
    for paper in papers:
        pid = paper.get("paper_id", "")
        if pid:
            sections[0]["mounted_paper_ids"].append(pid)
            sections[2]["mounted_paper_ids"].append(pid)

    return {
        "sections": sections,
        "subtopics": [],
    }
