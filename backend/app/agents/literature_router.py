"""Literature turn intent router — simplified 3-intent version.

Intents:
- new_topic: first turn (user_turns <= 1), full pipeline
- append_urls: turn 2+ with URLs, fetch + rewrite
- query_corpus: everything else (fallback), QA from existing corpus
"""
from __future__ import annotations

import re
from typing import Any

_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def _contains_url(message: str) -> bool:
    """Check if message contains an http(s) URL."""
    return bool(_URL_PATTERN.search(message))


def route_intent(
    *,
    user_turns: int,
    message: str,
    fetch_urls: list[str],
    has_corpus: bool,
) -> str:
    """Determine the intent for the current user turn.

    Rules (by priority):
    1. user_turns <= 1 → new_topic
    2. Has fetch_urls or message contains URL → append_urls
    3. Everything else → query_corpus
    """
    if user_turns <= 1:
        return "new_topic"

    if fetch_urls or _contains_url(message):
        return "append_urls"

    return "query_corpus"


async def route_intent_with_llm(
    *,
    message: str,
    has_corpus: bool,
    llm: Any = None,
) -> str:
    """LLM-assisted intent routing (fallback when rules ambiguous).

    For simplified version, delegates to rule-based routing.
    LLM can be used for edge cases in future.
    """
    # Rule-based is sufficient for 3-intent simplified version
    # LLM would only be needed if we needed to distinguish
    # between query types within query_corpus
    return "query_corpus"
