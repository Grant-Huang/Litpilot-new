"""OpenAI-compatible LLM client (covers openai/zhipu/alibaba/minimax/ollama)."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from app.llm.base import LLMMessage, LLMResponse

_log = logging.getLogger(__name__)


class OpenAICompatLLM:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        model: str = "",
        group_id: str = "",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.group_id = group_id
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> LLMResponse:
        payload = self._build_payload(
            messages, system=system, max_tokens=max_tokens,
            temperature=temperature, stream=False,
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
        if resp.status_code != 200:
            raise Exception(
                f"LLM chat failed: status={resp.status_code} body={resp.text[:500]}"
            )
        data = resp.json()
        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage"),
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        payload = self._build_payload(
            messages, system=system, max_tokens=max_tokens,
            temperature=temperature, stream=True,
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content

    def _build_payload(
        self,
        messages: list[LLMMessage],
        *,
        system: str,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> dict:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        for m in messages:
            msgs.append({"role": m.role, "content": m.content})
        payload: dict = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if stream:
            payload["stream"] = True
        return payload
