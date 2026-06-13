"""Search merge — deduplicate and merge hits from multiple sources."""
from __future__ import annotations


def merge_search_hits(
    hit_lists: list[list[dict[str, str]]],
) -> list[dict[str, str]]:
    """Merge hits from multiple sources, deduplicating by URL.

    Preserves first-seen order; enriches with source provenance.
    """
    seen_urls: dict[str, dict[str, str]] = {}

    for hits in hit_lists:
        for hit in hits:
            url = str(hit.get("url") or "").strip()
            if not url:
                continue
            normalized = _normalize_url(url)
            if normalized in seen_urls:
                existing = seen_urls[normalized]
                _enrich_existing(existing, hit)
                continue
            entry = dict(hit)
            entry["url"] = url
            seen_urls[normalized] = entry

    return list(seen_urls.values())


def _normalize_url(url: str) -> str:
    """Normalize URL for dedup: lowercase host, strip trailing slash, strip fragment."""
    url = url.strip()
    if url.startswith("https://"):
        rest = url[8:]
    elif url.startswith("http://"):
        rest = url[7:]
    else:
        return url.lower()

    parts = rest.split("/", 1)
    host = parts[0].lower()
    path = parts[1] if len(parts) > 1 else ""

    path = path.split("#")[0].split("?")[0]
    path = path.rstrip("/")

    return f"{host}/{path}" if path else host


def _enrich_existing(existing: dict[str, str], new_hit: dict[str, str]) -> None:
    """Merge metadata from new_hit into existing record."""
    if not existing.get("title") and new_hit.get("title"):
        existing["title"] = new_hit["title"]
    if not existing.get("snippet") and new_hit.get("snippet"):
        existing["snippet"] = new_hit["snippet"]
    existing_src = existing.get("source", "")
    new_src = new_hit.get("source", "")
    if new_src and new_src not in existing_src:
        existing["source"] = f"{existing_src},{new_src}".lstrip(",")
