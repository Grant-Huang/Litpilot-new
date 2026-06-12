"""Personal preferences — simplified version: no fields (APA-only)."""
from __future__ import annotations


def get_preferences() -> dict:
    """Return personal preferences (empty for simplified APA-only version)."""
    return {}


def put_preferences(payload: dict) -> dict:
    """Accept and ignore (APA-only, no configurable fields)."""
    return {}
