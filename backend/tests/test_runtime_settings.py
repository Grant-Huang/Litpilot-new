"""Tests for app.agents.runtime_settings."""
import os
from unittest.mock import patch

from app.agents.runtime_settings import build_runtime_settings


def test_defaults(tmp_path):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": str(cfg_dir)}, clear=False):
        settings = build_runtime_settings()
    assert settings["web_search_provider"] == "multi_academic"
    assert settings["web_fetch_provider"] == "native"
    assert settings["fetch_parallel"] == 3
    assert settings["max_fetch_urls"] == 5
    assert settings["citation_format"] == "apa"


def test_env_override(tmp_path):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    env = {
        "LITPILOT_CONFIG_DIR": str(cfg_dir),
        "TAVILY_API_KEY": "tvly-test",
        "JINA_API_KEY": "jina-test",
    }
    with patch.dict(os.environ, env, clear=False):
        settings = build_runtime_settings()
    assert settings["tavily_api_key"] == "tvly-test"
    assert settings["jina_api_key"] == "jina-test"


def test_capability_params_override(tmp_path):
    import json
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    cap_file = cfg_dir / "system.capabilities.json"
    cap_data = {
        "items": [{
            "capability_id": "web_search",
            "params": {
                "search_provider": "tavily",
                "search_max_results": 40,
            },
        }]
    }
    cap_file.write_text(json.dumps(cap_data), encoding="utf-8")
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": str(cfg_dir)}, clear=False):
        settings = build_runtime_settings()
    assert settings["search_max_results"] == 40


def test_orchestrator_fallback_to_review(tmp_path):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": str(cfg_dir)}, clear=False):
        settings = build_runtime_settings()
    assert settings["orchestrator"] == settings["review_main"]
