"""Prompt settings — runtime prompt/max_tokens reading with override."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.config.paths import config_dir
from app.agents.prompt_registry import PROMPT_META

_log = logging.getLogger(__name__)

_meta_by_key: dict[str, dict] = {m["key"]: m for m in PROMPT_META}
_cache: dict[str, Any] | None = None


def invalidate_cache() -> None:
    global _cache
    _cache = None


def _get_overrides() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    cfg = config_dir()
    cap_file = cfg / "system.capabilities.json"
    if not cap_file.exists():
        _cache = {}
        return _cache
    try:
        data = json.loads(cap_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _cache = {}
        return _cache
    params = {}
    for item in data.get("items", []):
        if item.get("capability_id") == "prompts":
            params = item.get("params", {})
            break
    _cache = params
    return _cache


async def get_prompt(key: str) -> str:
    """Return override or default prompt for key."""
    overrides = _get_overrides()
    custom = overrides.get(key, "")
    if custom and custom.strip():
        return custom
    from app.agents import prompt_registry as pr
    # Direct mapping: key -> DEFAULT_{KEY_STEM}
    _KEY_TO_ATTR = {
        "understanding_system_template": "DEFAULT_UNDERSTANDING_SYSTEM",
        "intent_router_system_template": "DEFAULT_INTENT_ROUTER_SYSTEM",
        "assessor_system_template": "DEFAULT_ASSESSOR_SYSTEM",
        "clarify_system_template": "DEFAULT_CLARIFY_SYSTEM",
        "search_refiner_system_template": "DEFAULT_SEARCH_REFINER_SYSTEM",
        "review_system_prompt_template": "DEFAULT_REVIEW_SYSTEM_PROMPT",
        "section_system_template": "DEFAULT_SECTION_SYSTEM",
        "attribute_system_template": "DEFAULT_ATTRIBUTE_SYSTEM",
        "summary_system_template": "DEFAULT_SUMMARY_SYSTEM",
        "query_corpus_system_template": "DEFAULT_QUERY_CORPUS_SYSTEM",
        "matrix_system_template": "DEFAULT_MATRIX_SYSTEM",
        "subtopic_tag_system": "DEFAULT_SUBTOPIC_TAG_SYSTEM",
    }
    attr_name = _KEY_TO_ATTR.get(key)
    if attr_name:
        return getattr(pr, attr_name, "")
    return ""


async def get_prompt_max_tokens(key: str) -> int:
    """Return max_tokens for key, clamped to [80, limit]."""
    overrides = _get_overrides()
    mt_key = f"{key}_max_tokens"
    if mt_key in overrides:
        val = overrides[mt_key]
        if isinstance(val, int) and val > 0:
            meta = _meta_by_key.get(key, {})
            limit = meta.get("max_tokens_limit", 8192)
            return max(80, min(val, limit))
    meta = _meta_by_key.get(key)
    if meta:
        return meta["default_max_tokens"]
    return 1024
