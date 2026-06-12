"""Tests for app.llm — base types and factory."""
from app.llm.base import LLMMessage


def test_llm_message():
    m = LLMMessage(role="user", content="hello")
    assert m.role == "user"
    assert m.content == "hello"


def test_llm_response():
    from app.llm.base import LLMResponse
    r = LLMResponse(content="world", finish_reason="stop", usage={"prompt_tokens": 5})
    assert r.content == "world"
    assert r.finish_reason == "stop"
    assert r.usage["prompt_tokens"] == 5
