"""Search aspect query resolution — map source name to search query."""
from __future__ import annotations


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
