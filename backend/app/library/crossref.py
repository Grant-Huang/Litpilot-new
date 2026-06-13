"""CrossRef utility re-exports — thin wrapper over metadata_fetch."""
from __future__ import annotations

from app.agents.tools.metadata_fetch import normalize_doi  # noqa: F401

__all__ = ["normalize_doi"]
