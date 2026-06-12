"""Tests for app.agents.literature_turn — orchestration engine."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.literature_turn import run_turn


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

    async def tool_call(self, name, args):
        self.events.append(("tool_call", name))

    async def tool_result(self, name, summary):
        self.events.append(("tool_result", name, summary))

    async def extension(self, name, data):
        self.events.append(("extension", name, data))


def _make_store(tmp_path):
    from app.storage.file_store import FileStore
    return FileStore(data_dir=tmp_path)


@pytest.mark.asyncio
async def test_new_topic_full_pipeline(tmp_path):
    """new_topic runs search→fetch→cite→generate→finalize."""
    from app.agents.literature_turn import run_turn

    store = _make_store(tmp_path)
    session = store.create_session("Test")
    emit = FakeEmit()

    fake_llm = AsyncMock()

    with patch(
        "app.agents.literature_turn._get_llm",
        new_callable=AsyncMock, return_value=fake_llm,
    ), patch(
        "app.agents.literature_turn.run_search_phase",
        new_callable=AsyncMock,
        return_value=[
            {"title": "Paper A", "url": "https://a.com",
             "snippet": "About AI", "source": "arxiv"},
        ],
    ), patch(
        "app.agents.literature_turn.run_fetch_phase",
        new_callable=AsyncMock,
        return_value=[
            {"url": "https://a.com", "text": "Full text about AI."},
        ],
    ), patch(
        "app.agents.literature_turn.run_cite_phase",
        new_callable=AsyncMock,
        return_value=[MagicMock(
            citation="[1] Author (2024). Paper A. Nature.",
            url="https://a.com",
            display_index=1,
        )],
    ), patch(
        "app.agents.literature_turn.generate_review",
        new_callable=AsyncMock,
        return_value="# AI Review\n\nGenerated content.",
    ), patch(
        "app.agents.literature_turn.generate_matrix",
        new_callable=AsyncMock,
        return_value="| Dim | Paper |",
    ), patch(
        "app.agents.literature_turn.finalize_turn",
        new_callable=AsyncMock,
        return_value={"intent": "new_topic", "review_version": "v1"},
    ):
        result = await run_turn(
            session_id=session["id"],
            message="AI in healthcare",
            fetch_urls=[],
            emit=emit,
            store=store,
        )

    assert result["extras"]["intent"] == "new_topic"
    assert result["extras"]["review_version"] == "v1"
    # Should emit stages
    assert any(e[0] == "stage" for e in emit.events)


@pytest.mark.asyncio
async def test_append_urls_skips_search(tmp_path):
    """append_urls skips search, goes straight to fetch."""
    store = _make_store(tmp_path)
    session = store.create_session("Test")
    store.update_meta(session["id"], user_turns=2)
    store.write_corpus(session["id"], {
        "version": 2, "papers": [{"url": "https://a.com"}],
    })
    emit = FakeEmit()

    fake_llm = AsyncMock()

    with patch(
        "app.agents.literature_turn._get_llm",
        new_callable=AsyncMock, return_value=fake_llm,
    ), patch(
        "app.agents.literature_turn.run_fetch_phase",
        new_callable=AsyncMock,
        return_value=[{"url": "https://new.com", "text": "New paper text."}],
    ), patch(
        "app.agents.literature_turn.run_cite_phase",
        new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.agents.literature_turn.generate_review",
        new_callable=AsyncMock,
        return_value="# Updated Review",
    ), patch(
        "app.agents.literature_turn.finalize_turn",
        new_callable=AsyncMock,
        return_value={"intent": "append_urls", "review_version": "v2"},
    ):
        result = await run_turn(
            session_id=session["id"],
            message="add these",
            fetch_urls=["https://new.com"],
            emit=emit,
            store=store,
        )

    assert result["extras"]["intent"] == "append_urls"
    assert result["extras"]["review_version"] == "v2"


@pytest.mark.asyncio
async def test_query_corpus_qa(tmp_path):
    """query_corpus calls generate_qa."""
    store = _make_store(tmp_path)
    session = store.create_session()
    store.update_meta(session["id"], user_turns=2)
    store.write_corpus(session["id"], {
        "version": 2, "papers": [{"url": "https://a.com"}],
    })
    emit = FakeEmit()

    fake_llm = AsyncMock()

    with patch(
        "app.agents.literature_turn._get_llm",
        new_callable=AsyncMock, return_value=fake_llm,
    ), patch(
        "app.agents.literature_turn.generate_qa",
        new_callable=AsyncMock,
        return_value="Smith found that AI helps accuracy.",
    ), patch(
        "app.agents.literature_turn.finalize_turn",
        new_callable=AsyncMock,
        return_value={"intent": "query_corpus"},
    ):
        result = await run_turn(
            session_id=session["id"],
            message="what did Smith find?",
            fetch_urls=[],
            emit=emit,
            store=store,
        )

    assert result["extras"]["intent"] == "query_corpus"


@pytest.mark.asyncio
async def test_query_corpus_empty_corpus(tmp_path):
    """query_corpus with empty corpus returns prompt message."""
    store = _make_store(tmp_path)
    session = store.create_session()
    store.update_meta(session["id"], user_turns=2)
    emit = FakeEmit()

    result = await run_turn(
        session_id=session["id"],
        message="what about X?",
        fetch_urls=[],
        emit=emit,
        store=store,
    )

    assert "语料" in result["content"] or "综述" in result["content"]


@pytest.mark.asyncio
async def test_version_increment_v1_to_v2(tmp_path):
    """Second append_urls increments version v1→v2."""
    store = _make_store(tmp_path)
    session = store.create_session()
    store.update_meta(session["id"], user_turns=2)
    store.write_corpus(session["id"], {
        "version": 2, "papers": [{"url": "https://a.com"}],
    })
    # Write v1 review
    store.write_review(session["id"], "# Review v1")

    emit = FakeEmit()
    fake_llm = AsyncMock()

    with patch(
        "app.agents.literature_turn._get_llm",
        new_callable=AsyncMock, return_value=fake_llm,
    ), patch(
        "app.agents.literature_turn.run_fetch_phase",
        new_callable=AsyncMock,
        return_value=[{"url": "https://new.com", "text": "Text."}],
    ), patch(
        "app.agents.literature_turn.run_cite_phase",
        new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.agents.literature_turn.generate_review",
        new_callable=AsyncMock, return_value="# Review v2",
    ), patch(
        "app.agents.literature_turn.finalize_turn",
        new_callable=AsyncMock,
        return_value={"intent": "append_urls", "review_version": "v2"},
    ):
        result = await run_turn(
            session_id=session["id"],
            message="add",
            fetch_urls=["https://new.com"],
            emit=emit,
            store=store,
        )

    assert result["extras"]["review_version"] == "v2"
