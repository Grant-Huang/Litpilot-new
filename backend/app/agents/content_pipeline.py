"""Content pipeline — assemble materials for LLM consumption.

Produces multi-section text with labeled blocks:
- [web_search] — search hit summaries
- [网页材料] — fetched full texts (truncated)
- [Citations] — formatted citation entries (APA)
- [已生成综述] — prior review (for query_corpus only)
"""
from __future__ import annotations


def build_review_materials(
    *,
    search_hits: list[dict[str, str]],
    fetch_texts: list[dict[str, str]],
    citations: list[str],
    max_source_chars: int = 14000,
) -> str:
    """Assemble materials for review/matrix generation."""
    parts: list[str] = []

    # [web_search] section
    if search_hits:
        lines = ["[web_search]"]
        for i, hit in enumerate(search_hits, 1):
            title = hit.get("title", "Untitled")
            snippet = hit.get("snippet", "")
            url = hit.get("url", "")
            lines.append(f"{i}. {title} — {snippet} ({url})")
        parts.append("\n".join(lines))

    # [网页材料] section
    if fetch_texts:
        lines = ["[网页材料]"]
        for ft in fetch_texts:
            url = ft.get("url", "")
            text = ft.get("text", "")
            if len(text) > max_source_chars:
                text = text[:max_source_chars] + "\n…（截断）"
            lines.append(f"--- {url} ---\n{text}")
        parts.append("\n".join(lines))

    # [Citations] section
    if citations:
        lines = ["[Citations]"]
        for cite in citations:
            lines.append(cite)
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def build_qa_materials(
    *,
    prior_review: str = "",
    search_hits: list[dict[str, str]] | None = None,
    fetch_texts: list[dict[str, str]] | None = None,
    citations: list[str] | None = None,
    max_source_chars: int = 14000,
) -> str:
    """Assemble materials for query_corpus QA.

    Same as build_review_materials but adds [已生成综述] section.
    """
    parts: list[str] = []

    # [已生成综述] — primary evidence for QA
    if prior_review and prior_review.strip():
        parts.append(f"[已生成综述]\n{prior_review}")

    # Remaining materials
    base = build_review_materials(
        search_hits=search_hits or [],
        fetch_texts=fetch_texts or [],
        citations=citations or [],
        max_source_chars=max_source_chars,
    )
    if base:
        parts.append(base)

    return "\n\n".join(parts)
