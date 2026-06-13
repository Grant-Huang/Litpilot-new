"""Search query refiner — apply academic search suffixes to queries."""
from __future__ import annotations


def apply_academic_search_suffix(query: str) -> str:
    """Append academic search suffix to improve result quality.

    Adds common academic terms to improve scholarly search results.
    """
    if not query or not query.strip():
        return query
    q = query.strip()
    if any(kw in q.lower() for kw in ("review", "survey", "综述")):
        return q
    return f"{q} literature review"
