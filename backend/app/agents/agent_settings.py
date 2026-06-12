"""Configuration getters consumed by ref tools (async, from runtime_settings)."""
from __future__ import annotations

from app.agents.runtime_settings import build_runtime_settings

_settings_cache: dict | None = None


def _get_settings() -> dict:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = build_runtime_settings()
    return _settings_cache


def invalidate_cache() -> None:
    global _settings_cache
    _settings_cache = None


async def get_web_search_provider() -> str:
    return _get_settings().get("web_search_provider", "multi_academic")


async def get_web_fetch_provider() -> str:
    return _get_settings().get("web_fetch_provider", "native")


async def get_pdf_extract_backend() -> str:
    return _get_settings().get("pdf_extract_backend", "pymupdf4llm")


async def get_s2_api_key() -> str:
    return _get_settings().get("s2_api_key", "")


async def get_jina_reader_api_key() -> str:
    return _get_settings().get("jina_api_key", "")


async def get_fetch_parallel() -> int:
    val = _get_settings().get("fetch_parallel", 3)
    return max(1, min(val, 8))


async def get_review_llm_config() -> dict:
    return _get_settings().get("review_main", {})


async def get_orchestrator_llm_config() -> dict:
    settings = _get_settings()
    return settings.get("orchestrator", settings.get("review_main", {}))


async def get_web_search_api_key() -> str:
    return _get_settings().get("tavily_api_key", "")
