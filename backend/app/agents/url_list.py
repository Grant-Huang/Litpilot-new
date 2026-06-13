"""URL list utilities — extract display title from search hit."""
from __future__ import annotations

from urllib.parse import urlparse


def title_from_search_hit(hit: dict) -> str:
    """Extract a display title from a search hit dict.

    Fallback chain: title → snippet[:80] → URL path → URL.
    """
    title = str(hit.get("title") or "").strip()
    if title:
        return title

    snippet = str(hit.get("snippet") or hit.get("content") or "").strip()
    if snippet:
        first_line = snippet.split("\n")[0].strip()
        return first_line[:80]

    url = str(hit.get("url") or "").strip()
    if url:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path:
            last = path.rsplit("/", maxsplit=1)[-1]
            last = last.replace("-", " ").replace("_", " ")
            if last:
                return last[:80]
        return parsed.netloc

    return ""
