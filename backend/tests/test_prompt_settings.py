"""Tests for app.agents.prompt_registry and prompt_settings."""
import pytest


def test_default_prompts_exist():
    from app.agents.prompt_registry import (
        DEFAULT_UNDERSTANDING_SYSTEM,
        DEFAULT_REVIEW_SYSTEM_PROMPT,
        PROMPT_META,
    )
    assert "文献综述助手" in DEFAULT_UNDERSTANDING_SYSTEM
    assert "APA" in DEFAULT_REVIEW_SYSTEM_PROMPT
    assert len(PROMPT_META) >= 8


def test_prompt_meta_keys():
    from app.agents.prompt_registry import PROMPT_META
    keys = [m["key"] for m in PROMPT_META]
    assert "understanding_system_template" in keys
    assert "review_system_prompt_template" in keys
    assert "attribute_system_template" in keys
    assert "query_corpus_system_template" in keys
    assert "matrix_system_template" in keys


@pytest.mark.asyncio
async def test_get_prompt_default():
    from app.agents.prompt_settings import get_prompt
    from app.agents.prompt_settings import invalidate_cache
    invalidate_cache()
    result = await get_prompt("attribute_system_template")
    assert "结构化" in result or "提取" in result


@pytest.mark.asyncio
async def test_get_prompt_unknown_key():
    from app.agents.prompt_settings import get_prompt, invalidate_cache
    invalidate_cache()
    result = await get_prompt("nonexistent_key")
    assert result == ""


@pytest.mark.asyncio
async def test_get_prompt_max_tokens_default():
    from app.agents.prompt_settings import get_prompt_max_tokens, invalidate_cache
    invalidate_cache()
    result = await get_prompt_max_tokens("attribute_system_template")
    assert 80 <= result <= 2000


@pytest.mark.asyncio
async def test_get_prompt_max_tokens_clamped():
    from app.agents.prompt_settings import get_prompt_max_tokens, invalidate_cache
    invalidate_cache()
    result = await get_prompt_max_tokens("nonexistent_key")
    assert result == 1024  # fallback
