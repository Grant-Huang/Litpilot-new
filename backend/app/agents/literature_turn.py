"""Literature turn orchestration — entry point for run_turn.

Routes to new_topic / append_urls / query_corpus pipelines,
delegates to pipeline/generate/finalize sub-modules.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

from app.agents.literature_router import route_intent
from app.agents.literature_clarification import (
    resolve_pending_gate,
)
from app.agents.literature_turn_pipeline import (
    run_search_phase,
    run_fetch_phase,
    run_cite_phase,
    build_corpus_papers,
    build_outline,
)
from app.agents.literature_turn_generate import (
    generate_review,
    generate_matrix,
    generate_qa,
)
from app.agents.literature_turn_finalize import finalize_turn
from app.agents.content_pipeline import build_review_materials, build_qa_materials
from app.llm.factory import build_client

_log = logging.getLogger(__name__)


class EmitFn(Protocol):  # noqa: E301
    async def stage(self, name: str, state: str) -> None: ...
    async def text(self, delta: str, **kw: Any) -> None: ...
    async def think(self, delta: str) -> None: ...
    async def artifact(  # noqa: E301
        self, id: str, lang: str, delta: str, **kw: Any
    ) -> None: ...
    async def tool_call(self, name: str, args: dict) -> None: ...
    async def tool_result(self, name: str, summary: str) -> None: ...
    async def extension(self, name: str, data: dict) -> None: ...


async def _get_llm() -> Any:
    """Build LLM client from current configuration."""
    from app.agents.agent_settings import get_review_llm_config
    cfg = await get_review_llm_config()
    return build_client(cfg)


async def run_turn(
    *,
    session_id: str,
    message: str,
    fetch_urls: list[str],
    emit: EmitFn,
    store: Any,
) -> dict:
    """Execute one turn. Returns assistant message dict for persistence."""
    meta = store.get_meta(session_id) or {}
    user_turns = meta.get("user_turns", 0)
    has_corpus = bool(
        store.read_corpus(session_id).get("papers")
    )

    # Check pending gate from previous turn
    pending = meta.get("pending_gate")
    if pending:
        resolution = resolve_pending_gate(pending, message)
        store.update_meta(
            session_id,
            pending_gate=None,
            resume_mode=resolution.get("resume_mode"),
        )
        if resolution["action"] == "cancel":
            store.update_meta(
                session_id,
                user_turns=user_turns + 1,
                last_intent="cancelled",
            )
            return {
                "content": "已取消。",
                "extras": {"intent": "cancelled", "delivery": "chat"},
            }
        intent = "new_topic"
    else:
        # Use incremented turn count for routing: first message is turn 1
        intent = route_intent(
            user_turns=user_turns + 1,
            message=message,
            fetch_urls=fetch_urls,
            has_corpus=has_corpus,
        )

    # Update turn count BEFORE execution so concurrent turns route correctly
    store.update_meta(
        session_id,
        user_turns=user_turns + 1,
        last_intent=intent,
        initial_query=meta.get("initial_query") or message,
    )

    await emit.extension("literature_intent", {
        "intent": intent,
        "use_existing_corpus": has_corpus,
    })

    llm = await _get_llm()

    if intent == "new_topic":
        result = await _run_new_topic(
            session_id=session_id,
            message=message,
            fetch_urls=fetch_urls,
            emit=emit,
            store=store,
            llm=llm,
            meta=meta,
        )
    elif intent == "append_urls":
        result = await _run_append_urls(
            session_id=session_id,
            message=message,
            fetch_urls=fetch_urls,
            emit=emit,
            store=store,
            llm=llm,
        )
    else:
        result = await _run_query_corpus(
            session_id=session_id,
            message=message,
            emit=emit,
            store=store,
            llm=llm,
        )

    return result


async def _run_new_topic(
    *,
    session_id: str,
    message: str,
    fetch_urls: list[str],
    emit: EmitFn,
    store: Any,
    llm: Any,
    meta: dict,
) -> dict:
    """Full pipeline: understand → search → fetch → cite → generate."""
    # ── Understand ──
    await emit.stage("理解研究问题", "active")
    await emit.text("正在理解您的研究主题…", delivery="process")
    await emit.stage("理解研究问题", "done")

    session_title = meta.get("title") or message[:50]
    search_query = message  # simplified: use message as query directly

    # ── Search ──
    await emit.stage("文献检索", "active")
    await emit.text("检索中…", delivery="process")

    from app.agents.agent_settings import get_web_search_api_key
    api_key = await get_web_search_api_key()

    hits = await run_search_phase(
        queries=[search_query],
        emit=emit,
        api_key=api_key or "",
    )

    await emit.stage("文献检索", "done")

    if not hits and not fetch_urls:
        return {
            "content": "未检索到相关文献。请尝试更具体的主题或提供文献链接。",
            "extras": {
                "delivery": "chat",
                "artifactKind": "none",
                "intent": "new_topic",
            },
        }

    # ── Fetch ──
    await emit.stage("抓取全文", "active")
    fetch_results = await run_fetch_phase(
        hits=hits,
        emit=emit,
        api_key=None,
    )
    await emit.stage("抓取全文", "done")

    # ── Cite ──
    await emit.stage("引用提取", "active")
    cite_records = await run_cite_phase(
        hits=hits,
        emit=emit,
        session_id=session_id,
        session_title=session_title,
    )
    citations = [r.citation for r in cite_records if hasattr(r, "citation")]
    await emit.stage("引用提取", "done")

    # ── Build corpus ──
    existing_corpus = store.read_corpus(session_id)
    corpus = build_corpus_papers(
        hits=hits,
        fetch_results=fetch_results,
        citations=cite_records,
        existing_corpus=existing_corpus,
    )

    # ── Build outline ──
    outline = build_outline(
        papers=corpus["papers"],
        search_aspects=[],
    )

    # ── Generate review ──
    search_hits_data = [
        {"title": h.get("title", ""), "snippet": h.get("snippet", ""),
         "url": h.get("url", "")}
        for h in hits
    ]
    fetch_data = [
        {"url": r.get("url", ""), "text": r.get("text", "")}
        for r in fetch_results
    ]

    materials = build_review_materials(
        search_hits=search_hits_data,
        fetch_texts=fetch_data,
        citations=citations,
    )

    review_text = await generate_review(
        materials=materials,
        llm=llm,
        emit=emit,
    )

    # ── Generate matrix ──
    matrix_text = ""
    if len(corpus["papers"]) >= 2:
        matrix_text = await generate_matrix(
            materials=materials,
            llm=llm,
            emit=emit,
        )

    # ── Finalize ──
    saved = await finalize_turn(
        session_id=session_id,
        store=store,
        intent="new_topic",
        review_text=review_text,
        matrix_text=matrix_text,
        corpus=corpus,
        outline=outline,
        citations=citations,
    )

    return {
        "content": "综述已生成。",
        "extras": {
            "delivery": "process",
            "artifactKind": "review",
            "intent": "new_topic",
            "executionTrace": [],
            "review_version": saved.get("review_version", "v1"),
        },
    }


async def _run_append_urls(
    *,
    session_id: str,
    message: str,
    fetch_urls: list[str],
    emit: EmitFn,
    store: Any,
    llm: Any,
) -> dict:
    """Append URLs pipeline: fetch → cite → rewrite full review."""
    # Convert fetch_urls to hits format
    url_hits = [
        {"title": url, "url": url, "snippet": "", "source": "user"}
        for url in fetch_urls
    ]

    # ── Fetch ──
    await emit.stage("抓取全文", "active")
    await emit.text("抓取用户提供的链接…", delivery="process")
    fetch_results = await run_fetch_phase(
        hits=url_hits,
        emit=emit,
        api_key=None,
    )
    await emit.stage("抓取全文", "done")

    # ── Cite ──
    await emit.stage("引用提取", "active")
    session_meta = store.get_meta(session_id) or {}
    cite_records = await run_cite_phase(
        hits=url_hits,
        emit=emit,
        session_id=session_id,
        session_title=session_meta.get("title", ""),
    )
    citations = [r.citation for r in cite_records if hasattr(r, "citation")]
    await emit.stage("引用提取", "done")

    # ── Build corpus (merge with existing) ──
    existing_corpus = store.read_corpus(session_id)
    corpus = build_corpus_papers(
        hits=url_hits,
        fetch_results=fetch_results,
        citations=cite_records,
        existing_corpus=existing_corpus,
    )

    # ── Build materials with all papers ──
    fetch_data = [
        {"url": r.get("url", ""), "text": r.get("text", "")}
        for r in fetch_results
    ]
    materials = build_review_materials(
        search_hits=[],
        fetch_texts=fetch_data,
        citations=citations,
    )

    # ── Rewrite full review ──
    review_text = await generate_review(
        materials=materials,
        llm=llm,
        emit=emit,
    )

    # ── Matrix ──
    matrix_text = ""
    if len(corpus["papers"]) >= 2:
        matrix_text = await generate_matrix(
            materials=materials,
            llm=llm,
            emit=emit,
        )

    # ── Finalize ──
    saved = await finalize_turn(
        session_id=session_id,
        store=store,
        intent="append_urls",
        review_text=review_text,
        matrix_text=matrix_text,
        corpus=corpus,
        outline=None,
        citations=citations,
    )

    return {
        "content": "综述已更新。",
        "extras": {
            "delivery": "process",
            "artifactKind": "review",
            "intent": "append_urls",
            "executionTrace": [],
            "review_version": saved.get("review_version", "v2"),
        },
    }


async def _run_query_corpus(
    *,
    session_id: str,
    message: str,
    emit: EmitFn,
    store: Any,
    llm: Any,
) -> dict:
    """QA from existing corpus. No artifact produced."""
    corpus = store.read_corpus(session_id)
    papers = corpus.get("papers", [])

    if not papers:
        return {
            "content": "当前会话尚无语料。请先描述研究主题以生成综述。",
            "extras": {
                "delivery": "chat",
                "artifactKind": "none",
                "intent": "query_corpus",
            },
        }

    # Read existing review
    versions = store.list_review_versions(session_id)
    prior_review = ""
    if versions:
        latest = versions[-1]
        prior_review = store.read_review(session_id, latest) or ""

    # Build QA materials
    citations: list[str] = []
    fetch_texts = [
        {"url": p.get("url", ""), "text": p.get("snippet", "")}
        for p in papers[:10]
    ]

    materials = build_qa_materials(
        prior_review=prior_review,
        fetch_texts=fetch_texts,
        citations=citations,
    )

    answer = await generate_qa(
        materials=materials,
        question=message,
        llm=llm,
        emit=emit,
    )

    await finalize_turn(
        session_id=session_id,
        store=store,
        intent="query_corpus",
    )

    return {
        "content": answer,
        "extras": {
            "delivery": "chat",
            "artifactKind": "none",
            "intent": "query_corpus",
        },
    }
