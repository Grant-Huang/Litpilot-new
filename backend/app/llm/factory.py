"""LLM factory — build client from config."""
from __future__ import annotations

from app.llm.openai_compat import OpenAICompatLLM


def build_client(cfg: dict) -> OpenAICompatLLM:
    return OpenAICompatLLM(
        base_url=cfg.get("base_url", "https://api.openai.com/v1"),
        api_key=cfg.get("api_key", ""),
        model=cfg.get("model", "gpt-4o"),
        group_id=cfg.get("group_id", ""),
    )
