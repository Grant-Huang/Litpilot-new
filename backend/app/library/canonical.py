"""Canonical key derivation for library deduplication."""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


def normalize_url(url: str) -> str:
    """Normalize URL: lowercase host, strip fragment/utm params/trailing slash."""
    if not url or not url.strip():
        return ""
    url = url.strip()
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{host}{port}"

    path = parsed.path.rstrip("/")

    # Strip utm_* params
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        cleaned = {k: v for k, v in params.items() if not k.startswith("utm_")}
        query = urlencode(cleaned, doseq=True)
    else:
        query = ""

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def canonical_key(*, url: str | None = None, doi: str | None = None) -> str:
    """Derive canonical key for dedup. DOI takes priority."""
    doi_clean = (doi or "").strip().lower()
    if doi_clean:
        return f"doi:{doi_clean}"
    url_norm = normalize_url(url or "")
    if url_norm:
        return f"url:{url_norm}"
    return ""
