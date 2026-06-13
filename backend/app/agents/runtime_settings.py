"""Runtime settings — merge system config + env + deploy defaults."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app.config.paths import config_dir

_log = logging.getLogger(__name__)

_DEPLOY_DEFAULTS_FILE = "deploy.defaults.json"

_DEFAULTS: dict[str, Any] = {
    "web_search_provider": "multi_academic",
    "search_max_results": 20,
    "search_retry_count": 3,
    "search_depth": "advanced",
    "include_domains": [
        "arxiv.org", "semanticscholar.org", "openalex.org",
        "crossref.org", "ncbi.nlm.nih.gov", "doi.org",
        "dl.acm.org", "ieeexplore.ieee.org", "springer.com",
        "nature.com", "sciencedirect.com", "wiley.com",
        "mdpi.com", "frontiersin.org", "biorxiv.org",
        "medrxiv.org", "joss.theoj.org", "jmlr.org",
        "neurips.cc", "openreview.net", "aclanthology.org",
        "dblp.org", "ssrn.com",
    ],
    "exclude_domains": [
        "youtube.com", "twitter.com", "facebook.com",
        "instagram.com", "tiktok.com", "reddit.com",
        "wikipedia.org", "linkedin.com", "pinterest.com",
        "quora.com", "medium.com", "patents.google.com",
        "amazon.com", "ebay.com",
    ],
    "enforce_domain_filter": True,
    "enable_junk_filter": True,
    "web_fetch_provider": "native",
    "pdf_extract_backend": "pymupdf4llm",
    "max_fetch_urls": 5,
    "fetch_parallel": 3,
    "fetch_timeout_sec": 45,
    "fetch_retry_count": 0,
    "max_source_chars": 14000,
    "citation_format": "apa",
}


def _read_json_safe(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def build_runtime_settings() -> dict[str, Any]:
    """Merge deploy defaults < env < system config into flat dict."""
    cfg = config_dir()
    result: dict[str, Any] = dict(_DEFAULTS)

    deploy = _read_json_safe(cfg / _DEPLOY_DEFAULTS_FILE)
    result.update(deploy)

    result["tavily_api_key"] = os.environ.get("TAVILY_API_KEY", "")
    result["brave_api_key"] = os.environ.get("BRAVE_API_KEY", "")
    result["jina_api_key"] = os.environ.get("JINA_API_KEY", "")
    result["s2_api_key"] = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    result["openai_api_key"] = os.environ.get("OPENAI_API_KEY", "")

    caps = _read_json_safe(cfg / "system.capabilities.json")
    for item in caps.get("items", []):
        cap_id = item.get("capability_id", "")
        params = item.get("params", {})
        if cap_id == "web_search":
            for k in (
                "search_provider", "search_max_results", "search_retry_count",
                "search_depth", "include_domains", "exclude_domains",
                "enforce_domain_filter", "enable_junk_filter",
            ):
                if k in params:
                    result[k] = params[k]
            if "search_provider" in params:
                result["web_search_provider"] = params["search_provider"]
        elif cap_id == "web_fetch":
            for k in (
                "fetch_provider", "pdf_extract_backend", "max_fetch_urls",
                "fetch_parallel", "fetch_timeout_sec", "fetch_retry_count",
                "max_source_chars",
            ):
                if k in params:
                    result[k] = params[k]
            if "fetch_provider" in params:
                result["web_fetch_provider"] = params["fetch_provider"]

    creds = _read_json_safe(cfg / "system.credentials.json")
    cred_map: dict[str, dict] = {c["id"]: c for c in creds.get("items", [])}
    insts = _read_json_safe(cfg / "system.instances.json")
    inst_map: dict[str, dict] = {i["id"]: i for i in insts.get("items", [])}

    def _resolve_llm(cap_id: str) -> dict:
        for item in caps.get("items", []):
            if item.get("capability_id") == cap_id:
                ref = item.get("primary_ref")
                if ref and ref.get("kind") == "instance":
                    inst = inst_map.get(ref["id"], {})
                    cred_id = inst.get("credential_id", "")
                    cred = cred_map.get(cred_id, {}) if cred_id else {}
                    base_url = (
                        cred.get("base_url", "")
                        or inst.get("base_url", "")
                    )
                    api_key = (
                        cred.get("secret", "")
                        or inst.get("api_key", "")
                    )
                    provider = (
                        _provider_from_cred(cred.get("type", ""))
                        or inst.get("provider", "")
                    )
                    return {
                        "provider": provider,
                        "base_url": base_url,
                        "api_key": api_key,
                        "model": inst.get("model_name", ""),
                        "max_tokens": (item.get("params") or {}).get(
                            "max_tokens", 3000
                        ),
                    }
        return {}

    result["review_main"] = _resolve_llm("review_main") or {
        "provider": "openai",
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "model": "gpt-4o",
        "max_tokens": 3000,
    }
    result["orchestrator"] = (
        _resolve_llm("orchestrator") or result["review_main"]
    )

    return result


def _provider_from_cred(cred_type: str) -> str:
    if cred_type.startswith("llm:"):
        return cred_type[4:]
    return cred_type
