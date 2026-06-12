"""Metadata enrichment — Crossref + OpenAlex."""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


def _patch_from_crossref(data: dict) -> dict:
    msg = data.get("message", data)
    return {
        "citation_count": msg.get("is-referenced-by-count"),
        "references_count": msg.get("references-count"),
        "references_preview": [
            {"doi": r.get("DOI", "")}
            for r in (msg.get("reference") or [])[:30]
            if r.get("DOI")
        ],
        "venue": (msg.get("container-title") or [""])[0] or None,
        "year": str(msg.get("published-print", {}).get("date-parts", [[None]])[0][0])
        if msg.get("published-print")
        else None,
    }


def _patch_from_openalex(data: dict) -> dict:
    return {
        "doi": data.get("doi", "").replace("https://doi.org/", "")
        if data.get("doi") else None,
        "citation_count": data.get("cited_by_count"),
        "references_count": data.get("referenced_works_count"),
        "venue": (data.get("host_venue") or {}).get("display_name"),
        "year": str(data["publication_year"]) if data.get("publication_year") else None,
    }


async def enrich_one(record: Any) -> dict:
    """Enrich a single citation record via Crossref/OpenAlex.

    Returns a patch dict with any new metadata found.
    """
    import httpx

    patch: dict[str, Any] = {}
    doi = getattr(record, "doi", "") or ""

    if doi:
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"https://api.crossref.org/works/{doi}",
                    headers={"User-Agent": "LitPilot/0.1 (mailto:dev@litpilot.ai)"},
                )
                if resp.status_code == 200:
                    cr_patch = _patch_from_crossref(resp.json())
                    for k, v in cr_patch.items():
                        if v is not None:
                            patch[k] = v
            except Exception:
                _log.debug("Crossref lookup failed for %s", doi, exc_info=True)

    if not doi:
        title = getattr(record, "title", "") or ""
        first_author = ""
        authors = getattr(record, "authors", "")
        if isinstance(authors, str) and authors:
            first_author = authors.split(",")[0].strip()

        if title:
            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    query_parts = [title[:100]]
                    if first_author:
                        query_parts.append(first_author)
                    resp = await client.get(
                        "https://api.openalex.org/works",
                        params={"search": " ".join(query_parts), "per_page": 1},
                    )
                    if resp.status_code == 200:
                        results = resp.json().get("results", [])
                        if results:
                            oa = results[0]
                            oa_patch = _patch_from_openalex(oa)
                            for k, v in oa_patch.items():
                                if v is not None:
                                    patch[k] = v
                except Exception:
                    _log.debug("OpenAlex lookup failed", exc_info=True)

    return patch


async def enrich_records_parallel(
    records: list, *, parallel: int = 3
) -> list[dict]:
    """Enrich multiple records in parallel. Returns patch list (same order)."""
    import asyncio

    sem = asyncio.Semaphore(max(1, min(parallel, 12)))

    async def _one(rec):
        async with sem:
            return await enrich_one(rec)

    return list(await asyncio.gather(*[_one(r) for r in records]))
