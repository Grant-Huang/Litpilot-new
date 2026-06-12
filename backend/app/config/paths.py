"""Path resolution for data and config directories."""
from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Return data directory path (env LITPILOT_DATA_DIR overrides default)."""
    raw = os.environ.get("LITPILOT_DATA_DIR", "data")
    return Path(raw).resolve()


def config_dir() -> Path:
    """Return config directory path (env LITPILOT_CONFIG_DIR overrides default)."""
    raw = os.environ.get("LITPILOT_CONFIG_DIR", "config")
    return Path(raw).resolve()


def ensure_dir(path: Path) -> None:
    """Create directory (and parents) if not exists."""
    path.mkdir(parents=True, exist_ok=True)
