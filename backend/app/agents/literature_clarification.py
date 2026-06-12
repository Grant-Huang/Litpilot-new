"""Literature clarification gates — first_turn, search_zero, outline_confirm."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class ClarificationGate:
    kind: str
    prompt: str
    options: list[str] | None = None


def check_clarification_gate(
    *,
    meta: dict[str, Any],
    message: str,
    confidence: float = 1.0,
    search_zero: bool = False,
    plan_confirm: bool = False,
) -> dict | None:
    """Check if a clarification gate should be triggered.

    Returns a gate dict if triggered, None otherwise.
    Gates: first_turn (confidence < 0.6), search_zero, outline_confirm.
    """
    # Don't stack gates
    if meta.get("pending_gate"):
        return None

    # Only apply first_turn gate on first turn
    if meta.get("user_turns", 0) <= 1:
        # search_zero takes priority
        if search_zero:
            return {
                "kind": "search_zero",
                "prompt": "检索未找到相关文献。您可以放宽域名限制、更换关键词或取消。",
                "options": ["放宽域名限制", "更换关键词", "取消"],
            }

        # confidence gate
        if confidence < 0.6:
            return {
                "kind": "first_turn",
                "prompt": f"您的研究主题「{message[:50]}」表述较模糊，请补充更多细节以便准确理解。",
                "options": ["补充主题说明", "换个方向"],
            }

        # outline_confirm gate
        if plan_confirm and meta.get("outline_mode") in ("full", "lite"):
            return {
                "kind": "outline_confirm",
                "prompt": "大纲已经生成。您可以确认继续撰写综述，或修改大纲后重新生成。",
                "options": [
                    "确认继续撰写综述",
                    "修改大纲并重新生成",
                    "添加/删除子主题",
                ],
            }

    return None


def resolve_pending_gate(
    gate: dict[str, Any],
    user_message: str,
) -> dict[str, Any]:
    """Resolve a pending gate based on user response.

    Returns action dict with 'action' and optional 'resume_mode'.
    """
    kind = gate.get("kind", "")
    msg_lower = user_message.lower().strip()

    if kind == "first_turn":
        # User provided more info → restart understanding
        return {"action": "restart_understand", "resume_mode": None}

    if kind == "search_zero":
        if "取消" in msg_lower or "cancel" in msg_lower:
            return {"action": "cancel", "resume_mode": None}
        return {"action": "restart_search", "resume_mode": None}

    if kind == "outline_confirm":
        if any(kw in msg_lower for kw in ("修改", "modify", "添加", "删除", "改")):
            return {"action": "restart_understand", "resume_mode": None}
        return {"action": "resume", "resume_mode": "generate_only"}

    return {"action": "restart_understand", "resume_mode": None}
