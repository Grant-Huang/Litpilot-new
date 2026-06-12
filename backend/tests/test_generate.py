"""Tests for app.agents.literature_turn_generate — review/matrix/QA generation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class FakeEmit:
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

    async def extension(self, name, data):
        self.events.append(("extension", name, data))


@pytest.mark.asyncio
async def test_generate_review_streams_artifact():
    """generate_review streams review content as artifact."""
    from app.agents.literature_turn_generate import generate_review

    emit = FakeEmit()
    fake_llm = AsyncMock()
    fake_llm.stream = MagicMock(
        return_value=aiter(["# Review\n\n", "Content paragraph.", "More text."])
    )

    with patch(
        "app.agents.literature_turn_generate.get_prompt",
        new_callable=AsyncMock, return_value="Write a review.",
    ), patch(
        "app.agents.literature_turn_generate.get_prompt_max_tokens",
        new_callable=AsyncMock, return_value=3000,
    ):
        result = await generate_review(
            materials="[web_search]\nPaper A\n\n[Citations]\n[1] Author",
            llm=fake_llm,
            emit=emit,
        )

    assert result is not None
    assert len(result) > 0
    # Should have emitted artifact events
    assert any(e[0] == "artifact" and e[1] == "review-latest"
               for e in emit.events)


@pytest.mark.asyncio
async def test_generate_matrix():
    """generate_matrix creates matrix artifact."""
    from app.agents.literature_turn_generate import generate_matrix

    emit = FakeEmit()
    fake_llm = AsyncMock()
    fake_llm.chat = AsyncMock(
        return_value=MagicMock(
            content="| Dimension | Paper A |\n|---|---|\n| Method | DL |"
        )
    )

    with patch(
        "app.agents.literature_turn_generate.get_prompt",
        new_callable=AsyncMock, return_value="Generate matrix.",
    ), patch(
        "app.agents.literature_turn_generate.get_prompt_max_tokens",
        new_callable=AsyncMock, return_value=4096,
    ):
        result = await generate_matrix(
            materials="[Citations]\n[1] Paper A",
            llm=fake_llm,
            emit=emit,
        )

    assert result is not None
    assert "Dimension" in result
    assert any(e[0] == "artifact" and e[1] == "matrix-latest"
               for e in emit.events)


@pytest.mark.asyncio
async def test_generate_qa_answer():
    """generate_qa returns short answer."""
    from app.agents.literature_turn_generate import generate_qa

    emit = FakeEmit()
    fake_llm = AsyncMock()
    fake_llm.chat = AsyncMock(
        return_value=MagicMock(content="Smith found that AI improves accuracy.")
    )

    with patch(
        "app.agents.literature_turn_generate.get_prompt",
        new_callable=AsyncMock, return_value="Answer from review.",
    ), patch(
        "app.agents.literature_turn_generate.get_prompt_max_tokens",
        new_callable=AsyncMock, return_value=2048,
    ):
        result = await generate_qa(
            materials="[已生成综述]\nReview content.\n\n[Citations]\n[1] Smith",
            question="what did Smith find?",
            llm=fake_llm,
            emit=emit,
        )

    assert result == "Smith found that AI improves accuracy."
    assert any(e[0] == "stage" and e[1] == "语料问答" for e in emit.events)


async def aiter(items):
    for item in items:
        yield item
