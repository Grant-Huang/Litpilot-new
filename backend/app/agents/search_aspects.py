"""Search aspect query resolution — map source name to search query."""
from __future__ import annotations

from typing import Any


DEFAULT_SEARCH_EXCLUDE_TERMS: list[str] = []


def merge_exclude_terms(
    *term_lists: list[str] | Any,
) -> list[str]:
    """Merge multiple exclude-term lists into one deduplicated list."""
    merged: list[str] = []
    seen: set[str] = set()
    for lst in term_lists:
        if not isinstance(lst, (list, tuple)):
            continue
        for term in lst:
            t = str(term).strip().lower()
            if t and t not in seen:
                seen.add(t)
                merged.append(t)
    return merged


def query_for_source(
    source_name: str,
    *,
    source_queries: dict[str, str] | None = None,
    fallback: str = "",
) -> str:
    """Resolve query string for a specific search source.

    Looks up source_name in source_queries dict, returns fallback if not found.
    """
    if source_queries:
        q = source_queries.get(source_name, "")
        if q and q.strip():
            return q.strip()
    return fallback.strip()
