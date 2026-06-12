"""Literature turn generate — review / matrix / QA generation.

Uses LLM to produce review, matrix, and QA answers.
Emits artifacts and text via the emit protocol.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.prompt_settings import get_prompt, get_prompt_max_tokens
from app.llm.base import LLMMessage

_log = logging.getLogger(__name__)


async def generate_review(
    *,
    materials: str,
    llm: Any,
    emit: Any,
) -> str:
    """Generate a literature review via streaming LLM.

    Returns the complete review text.
    """
    system = await get_prompt("review_system_prompt_template")
    max_tokens = await get_prompt_max_tokens("review_system_prompt_template")

    user_msg = f"{materials}\n\n请根据以上材料撰写文献综述。"

    await emit.stage("综述生成", "active")

    chunks: list[str] = []
    async for chunk in llm.stream(
        [LLMMessage(role="user", content=user_msg)],
        system=system,
        max_tokens=max_tokens,
        temperature=0.3,
    ):
        chunks.append(chunk)
        await emit.artifact("review-latest", "markdown", chunk)

    # Mark artifact as done
    await emit.artifact("review-latest", "markdown", "", done=True)
    await emit.stage("综述生成", "done")

    return "".join(chunks)


async def generate_matrix(
    *,
    materials: str,
    llm: Any,
    emit: Any,
) -> str:
    """Generate a synthesis matrix via LLM (non-streaming).

    Returns the matrix markdown text.
    """
    system = await get_prompt("matrix_system_template")
    max_tokens = await get_prompt_max_tokens("matrix_system_template")

    user_msg = f"{materials}\n\n请根据以上材料生成 Synthesis Matrix。"

    await emit.stage("矩阵生成", "active")

    resp = await llm.chat(
        [LLMMessage(role="user", content=user_msg)],
        system=system,
        max_tokens=max_tokens,
        temperature=0.2,
    )

    content = resp.content or ""
    await emit.artifact(
        "matrix-latest", "literature-matrix+markdown",
        content, done=True,
    )
    await emit.stage("矩阵生成", "done")

    return content


async def generate_qa(
    *,
    materials: str,
    question: str,
    llm: Any,
    emit: Any,
) -> str:
    """Generate a QA answer from existing corpus.

    Returns the answer text (≤500 chars expected).
    """
    system = await get_prompt("query_corpus_system_template")
    max_tokens = await get_prompt_max_tokens("query_corpus_system_template")

    user_msg = (
        f"{materials}\n\n"
        f"用户问题：{question}\n\n"
        f"请根据以上材料回答问题，简洁准确，不超过 500 字。"
    )

    await emit.stage("语料问答", "active")

    resp = await llm.chat(
        [LLMMessage(role="user", content=user_msg)],
        system=system,
        max_tokens=max_tokens,
        temperature=0.2,
    )

    content = resp.content or ""
    await emit.text(content, delivery="chat")
    await emit.stage("语料问答", "done")

    return content
