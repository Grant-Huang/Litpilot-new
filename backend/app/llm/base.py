"""LLM client abstraction — messages, response, protocol."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class LLMResponse:
    content: str
    finish_reason: str = "stop"
    usage: dict[str, Any] | None = None
