"""Tests for app.llm.openai_compat — OpenAI-compatible LLM client."""
import json

import httpx
import pytest
import respx

from app.llm.base import LLMMessage
from app.llm.openai_compat import OpenAICompatLLM


@pytest.fixture
def llm():
    return OpenAICompatLLM(
        base_url="https://api.test.com/v1",
        api_key="test-key",
        model="test-model",
    )


@pytest.mark.asyncio
async def test_chat_success(llm):
    with respx.mock:
        respx.post("https://api.test.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "hello back"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                },
            )
        )
        resp = await llm.chat(
            [LLMMessage(role="user", content="hello")],
            system="You are helpful",
            max_tokens=100,
            temperature=0.5,
        )
    assert resp.content == "hello back"
    assert resp.finish_reason == "stop"
    assert resp.usage["prompt_tokens"] == 3


@pytest.mark.asyncio
async def test_chat_error(llm):
    with respx.mock:
        respx.post("https://api.test.com/v1/chat/completions").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(Exception, match="LLM chat failed"):
            await llm.chat([LLMMessage(role="user", content="hi")])


@pytest.mark.asyncio
async def test_stream_yields_deltas(llm):
    chunks = [
        {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": " world"}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    ]
    sse_lines = []
    for chunk in chunks:
        sse_lines.append(f"data: {json.dumps(chunk)}")
    sse_lines.append("data: [DONE]")

    body = "\n".join(sse_lines) + "\n\n"

    with respx.mock:
        respx.post("https://api.test.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                content=body.encode(),
                headers={"content-type": "text/event-stream"},
            )
        )
        deltas = []
        async for delta in llm.stream(
            [LLMMessage(role="user", content="hi")],
            system="sys",
        ):
            deltas.append(delta)
    assert deltas == ["Hello", " world"]
