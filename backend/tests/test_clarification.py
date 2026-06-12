"""Tests for app.agents.literature_clarification — clarification gates."""
from app.agents.literature_clarification import (
    check_clarification_gate,
    resolve_pending_gate,
)


def test_first_turn_short_brief_triggers_gate():
    meta = {"user_turns": 1, "pending_gate": None}
    result = check_clarification_gate(
        meta=meta, message="MOM", confidence=0.3
    )
    assert result is not None
    assert result["kind"] == "first_turn"
    assert result["prompt"] != ""


def test_first_turn_confident_no_gate():
    meta = {"user_turns": 1, "pending_gate": None}
    result = check_clarification_gate(
        meta=meta,
        message="Please review AI-native manufacturing operations management",
        confidence=0.9,
    )
    assert result is None


def test_search_zero_triggers_gate():
    meta = {"user_turns": 1, "pending_gate": None}
    result = check_clarification_gate(
        meta=meta,
        message="quantum computing in healthcare",
        confidence=0.8,
        search_zero=True,
    )
    assert result is not None
    assert result["kind"] == "search_zero"


def test_outline_confirm_triggers_gate():
    meta = {"user_turns": 1, "pending_gate": None, "outline_mode": "full"}
    result = check_clarification_gate(
        meta=meta,
        message="review AI",
        confidence=0.8,
        plan_confirm=True,
    )
    assert result is not None
    assert result["kind"] == "outline_confirm"


def test_no_gate_when_already_pending():
    meta = {
        "user_turns": 2,
        "pending_gate": {"kind": "first_turn", "prompt": "Clarify?"},
    }
    result = check_clarification_gate(
        meta=meta, message="more info", confidence=0.5
    )
    assert result is None  # don't stack gates


def test_resolve_first_turn_continue():
    gate = {"kind": "first_turn", "prompt": "Clarify?"}
    result = resolve_pending_gate(gate, user_message="I mean MOM operations")
    assert result["action"] == "restart_understand"
    assert result["resume_mode"] is None


def test_resolve_search_zero_retry():
    gate = {"kind": "search_zero", "prompt": "No results found."}
    result = resolve_pending_gate(gate, user_message="try broader keywords")
    assert result["action"] == "restart_search"


def test_resolve_search_zero_cancel():
    gate = {"kind": "search_zero", "prompt": "No results."}
    result = resolve_pending_gate(gate, user_message="cancel")
    assert result["action"] == "cancel"


def test_resolve_outline_confirm():
    gate = {"kind": "outline_confirm", "prompt": "Confirm outline?"}
    result = resolve_pending_gate(gate, user_message="confirm")
    assert result["action"] == "resume"
    assert result["resume_mode"] == "generate_only"


def test_resolve_outline_modify():
    gate = {"kind": "outline_confirm", "prompt": "Confirm?"}
    result = resolve_pending_gate(gate, user_message="modify the outline")
    assert result["action"] == "restart_understand"


def test_no_gate_after_first_turn():
    meta = {"user_turns": 3, "pending_gate": None}
    result = check_clarification_gate(
        meta=meta, message="what about X?", confidence=0.5
    )
    assert result is None  # clarification only for first turn
