"""Upsert citation records into the global library (APA only)."""
from __future__ import annotations

import logging
from typing import Any

from app.library.canonical import canonical_key
from app.library.store import LibraryStore

_log = logging.getLogger(__name__)

_PROVENANCE_MAX = 20


def upsert_from_citation(
    rec: Any,
    *,
    lib: LibraryStore | None = None,
    citation_format: str = "apa",
    session_id: str = "",
    session_title: str = "",
    enrich_patch: dict | None = None,
) -> dict | None:
    """Upsert a CitationRecord into the global library.

    Returns the upserted item dict, or None if rec.success is False.
    """
    if not rec.success:
        return None

    if lib is None:
        lib = LibraryStore()

    ckey = canonical_key(doi=rec.doi, url=rec.url)
    existing = lib.get_by_key(ckey) if ckey else None

    if existing:
        return _merge_existing(
            lib, existing, rec, ckey, citation_format,
            session_id, session_title, enrich_patch,
        )
    else:
        return _create_new(
            lib, rec, ckey, citation_format,
            session_id, session_title, enrich_patch,
        )


def _create_new(
    lib: LibraryStore,
    rec: Any,
    ckey: str,
    citation_format: str,
    session_id: str,
    session_title: str,
    enrich_patch: dict | None,
) -> dict:
    idx = lib.alloc_display_index()
    apa_text = rec.to_apa(idx) if hasattr(rec, "to_apa") else ""
    provenance = []
    if session_id:
        provenance.append({
            "session_id": session_id,
            "role": "assistant",
            "session_title": session_title,
        })

    authors_raw = rec.authors if isinstance(rec.authors, list) else []
    if isinstance(rec.authors, str) and rec.authors:
        authors_raw = [a.strip() for a in rec.authors.split(",") if a.strip()]

    item: dict[str, Any] = {
        "id": existing_id if (existing_id := None) else _gen_id(),
        "display_index": idx,
        "canonical_key": ckey,
        "title": rec.title or "",
        "authors": authors_raw,
        "year": rec.year or "",
        "venue": rec.venue or "",
        "doi": rec.doi or "",
        "url": rec.url or "",
        "abstract": rec.abstract or "",
        "publisher": getattr(rec, "publisher", "") or "",
        "availability": {
            "has_abstract": bool(rec.abstract and len(rec.abstract) > 40),
            "has_full_text": False,
            "has_pdf": False,
            "fetch_status": "ok",
            "cite_status": "ok",
        },
        "citations": {"apa": apa_text},
        "provenance": provenance,
        "tags": [],
        "subtopic_tags": [],
        "starred": False,
    }

    if enrich_patch:
        _apply_enrich(item, enrich_patch)

    lib.put(item)
    return item


def _merge_existing(
    lib: LibraryStore,
    existing: dict,
    rec: Any,
    ckey: str,
    citation_format: str,
    session_id: str,
    session_title: str,
    enrich_patch: dict | None,
) -> dict:
    if not existing.get("title") and rec.title:
        existing["title"] = rec.title
    elif rec.title and len(rec.title) > len(existing.get("title", "")):
        existing["title"] = rec.title
    if not existing.get("abstract") and rec.abstract:
        existing["abstract"] = rec.abstract
    if not existing.get("doi") and rec.doi:
        existing["doi"] = rec.doi

    if session_id:
        prov = existing.setdefault("provenance", [])
        already = any(p.get("session_id") == session_id for p in prov)
        if not already and len(prov) < _PROVENANCE_MAX:
            prov.append({
                "session_id": session_id,
                "role": "assistant",
                "session_title": session_title,
            })

    if enrich_patch:
        _apply_enrich(existing, enrich_patch)

    lib.put(existing)
    return existing


def _apply_enrich(item: dict, patch: dict) -> None:
    for key in (
        "citation_count", "references_count", "references_preview",
        "venue", "year", "doi", "publisher",
    ):
        if key in patch and patch[key] and not item.get(key):
            item[key] = patch[key]
    if "citation_count" in patch and patch["citation_count"] is not None:
        item["citation_count"] = patch["citation_count"]
    if "references_count" in patch and patch["references_count"] is not None:
        item["references_count"] = patch["references_count"]
    if "references_preview" in patch and patch["references_preview"]:
        item["references_preview"] = patch["references_preview"]


def _gen_id() -> str:
    import secrets
    return secrets.token_hex(8)
