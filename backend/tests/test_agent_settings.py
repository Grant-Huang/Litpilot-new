"""Tests for app.agents.agent_settings."""
import os
from unittest.mock import patch

import pytest

from app.agents.agent_settings import (
    get_fetch_parallel,
    get_jina_reader_api_key,
    get_pdf_extract_backend,
    get_s2_api_key,
    get_web_fetch_provider,
    get_web_search_provider,
    invalidate_cache,
)


@pytest.mark.asyncio
async def test_get_web_search_provider_default(tmp_path):
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": str(tmp_path)}):
        result = await get_web_search_provider()
    assert result == "multi_academic"


@pytest.mark.asyncio
async def test_get_web_fetch_provider_default(tmp_path):
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": str(tmp_path)}):
        result = await get_web_fetch_provider()
    assert result == "native"


@pytest.mark.asyncio
async def test_get_pdf_extract_backend_default(tmp_path):
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": str(tmp_path)}):
        result = await get_pdf_extract_backend()
    assert result == "pymupdf4llm"


@pytest.mark.asyncio
async def test_get_fetch_parallel_default(tmp_path):
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": str(tmp_path)}):
        result = await get_fetch_parallel()
    assert result == 3


@pytest.mark.asyncio
async def test_get_s2_api_key_from_env(tmp_path):
    with patch.dict(
        os.environ,
        {"LITPILOT_CONFIG_DIR": str(tmp_path), "SEMANTIC_SCHOLAR_API_KEY": "s2test"},
    ):
        invalidate_cache()
        result = await get_s2_api_key()
    assert result == "s2test"


@pytest.mark.asyncio
async def test_get_jina_reader_api_key_from_env(tmp_path):
    with patch.dict(
        os.environ,
        {"LITPILOT_CONFIG_DIR": str(tmp_path), "JINA_API_KEY": "jinatest"},
    ):
        invalidate_cache()
        result = await get_jina_reader_api_key()
    assert result == "jinatest"


@pytest.mark.asyncio
async def test_get_fetch_parallel_clamped(tmp_path):
    import json
    cfg = tmp_path / "system.capabilities.json"
    cfg.write_text(json.dumps({
        "items": [{"capability_id": "web_fetch", "params": {"fetch_parallel": 100}}]
    }))
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": str(tmp_path)}):
        invalidate_cache()
        result = await get_fetch_parallel()
    assert result == 8
