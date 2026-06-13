"""Shared test fixtures — used by both unit and live tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class FakeEmit:
    """Collect events for assertion in unit tests."""

    def __init__(self):
        self.events = []

    async def stage(self, name, state):
        self.events.append(("stage", name, state))

    async def text(self, delta, **kw):
        self.events.append(("text", delta))

    async def think(self, delta):
        self.events.append(("think", delta))

    async def artifact(self, id, lang, delta, **kw):
        self.events.append(("artifact", id, delta))

    async def tool_call(self, name, args):
        self.events.append(("tool_call", name))

    async def tool_result(self, name, summary):
        self.events.append(("tool_result", name, summary))

    async def extension(self, name, data):
        self.events.append(("extension", name, data))


class LiveEmit:
    """Verbose emit that prints events for live test debugging."""

    def __init__(self, prefix: str = ""):
        self.events = []
        self.prefix = prefix

    async def stage(self, name, state):
        tag = f"[{self.prefix}]" if self.prefix else ""
        print(f"  {tag} STAGE {name}: {state}")
        self.events.append(("stage", name, state))

    async def text(self, delta, **kw):
        tag = f"[{self.prefix}]" if self.prefix else ""
        delivery = kw.get("delivery", "")
        print(f"  {tag} TEXT ({delivery}): {delta[:200]}")
        self.events.append(("text", delta))

    async def think(self, delta):
        tag = f"[{self.prefix}]" if self.prefix else ""
        print(f"  {tag} THINK: {delta[:200]}")
        self.events.append(("think", delta))

    async def artifact(self, id, lang, delta, **kw):
        tag = f"[{self.prefix}]" if self.prefix else ""
        done = kw.get("done", False)
        print(f"  {tag} ARTIFACT {id} ({lang}): +{len(delta)} chars"
              f"{' [DONE]' if done else ''}")
        self.events.append(("artifact", id, delta))

    async def tool_call(self, name, args):
        tag = f"[{self.prefix}]" if self.prefix else ""
        print(f"  {tag} TOOL_CALL {name}: {args}")
        self.events.append(("tool_call", name))

    async def tool_result(self, name, summary):
        tag = f"[{self.prefix}]" if self.prefix else ""
        print(f"  {tag} TOOL_RESULT {name}: {summary}")
        self.events.append(("tool_result", name))

    async def extension(self, name, data):
        tag = f"[{self.prefix}]" if self.prefix else ""
        print(f"  {tag} EXTENSION {name}: {data}")
        self.events.append(("extension", name))


def _make_store(tmp_path: Path) -> Any:
    from app.storage.file_store import FileStore
    return FileStore(data_dir=tmp_path)


@pytest.fixture
def store(tmp_path):
    return _make_store(tmp_path)


@pytest.fixture
def emit():
    return FakeEmit()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: marks tests as live integration (requires network/API)"
    )


def get_ref_list_urls() -> list[str]:
    """Read URLs from docs/ref/ref-list.txt."""
    base = Path(__file__).resolve().parent.parent.parent
    ref_file = base / "docs" / "ref" / "ref-list.txt"
    if not ref_file.exists():
        return []
    urls = []
    for line in ref_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and line.startswith("http"):
            urls.append(line)
    return urls


def skip_if_no_api_key(key_name: str):
    """Skip test if the required API key is not set in system config."""
    from app.agents.runtime_settings import build_runtime_settings
    settings = build_runtime_settings()
    val = settings.get(key_name, "")
    if not val:
        pytest.skip(f"Requires {key_name} in config (currently empty)")
    return val
