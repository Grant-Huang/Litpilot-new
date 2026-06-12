"""Tests for app.agents.literature_turn_pipeline — search/fetch/cite/outline."""
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
async def test_pipeline_search_emits_events(tmp_path):
    """Pipeline search phase emits tool_call/tool_result events."""
    from app.agents.literature_turn_pipeline import run_search_phase

    emit = FakeEmit()
    store = _make_store(tmp_path)
    store.create_session()

    search_results = {
        "results": [
            {"title": "AI Paper", "url": "https://arxiv.org/abs/2401.0001",
             "snippet": "About AI", "source": "arxiv"}
        ]
    }

    with patch(
        "app.agents.literature_turn_pipeline.cached_web_search",
        new_callable=AsyncMock, return_value=search_results,
    ):
        hits = await run_search_phase(
            queries=["AI in healthcare"],
            emit=emit,
            api_key="test-key",
        )

    assert len(hits) >= 1
    assert hits[0]["title"] == "AI Paper"
    # Should emit tool_call for search
    assert any(e[0] == "tool_call" for e in emit.events)


@pytest.mark.asyncio
async def test_pipeline_fetch_emits_events(tmp_path):
    """Pipeline fetch phase emits tool_call/tool_result."""
    from app.agents.literature_turn_pipeline import run_fetch_phase

    emit = FakeEmit()
    hits = [
        {"title": "Paper", "url": "https://example.com/paper",
         "snippet": "Summary", "source": "test"},
    ]

    with patch(
        "app.agents.literature_turn_pipeline.cached_web_fetch",
        new_callable=AsyncMock, return_value="Full paper text content.",
    ):
        results = await run_fetch_phase(
            hits=hits,
            emit=emit,
            api_key="",
        )

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/paper"
    assert results[0]["text"] == "Full paper text content."


@pytest.mark.asyncio
async def test_pipeline_cite_emits_events(tmp_path):
    """Pipeline cite phase calls extract_and_persist_batch."""
    from app.agents.literature_turn_pipeline import run_cite_phase

    emit = FakeEmit()
    hits = [
        {"title": "Paper A", "url": "https://a.com", "snippet": "S",
         "source": "test"},
    ]

    fake_cite = MagicMock()
    fake_cite.citation = "Author (2024). Title. Journal."
    fake_cite.url = "https://a.com"
    fake_cite.display_index = 1

    with patch(
        "app.agents.literature_turn_pipeline.extract_and_persist_batch",
        new_callable=AsyncMock, return_value=[fake_cite],
    ):
        citations = await run_cite_phase(
            hits=hits,
            emit=emit,
            session_id="test-session",
            session_title="Test",
        )

    assert len(citations) == 1
    assert citations[0].citation == "Author (2024). Title. Journal."


@pytest.mark.asyncio
async def test_pipeline_build_corpus(tmp_path):
    """build_corpus_papers creates paper_index entries."""
    from app.agents.literature_turn_pipeline import build_corpus_papers

    hits = [
        {"title": "Paper A", "url": "https://a.com",
         "snippet": "About AI", "source": "arxiv"},
    ]
    fetch_results = [
        {"url": "https://a.com", "text": "Full text."},
    ]

    corpus = build_corpus_papers(
        hits=hits,
        fetch_results=fetch_results,
        citations=[],
        existing_corpus={"version": 2, "papers": []},
    )

    assert len(corpus["papers"]) == 1
    assert corpus["papers"][0]["url"] == "https://a.com"
    assert corpus["papers"][0]["fetch_status"] == "fetched"


@pytest.mark.asyncio
async def test_pipeline_build_corpus_preserves_existing(tmp_path):
    """build_corpus_papers preserves existing papers."""
    from app.agents.literature_turn_pipeline import build_corpus_papers

    existing_paper = {
        "url": "https://existing.com",
        "title": "Existing Paper",
        "snippet": "Old",
        "source": "arxiv",
        "fetch_status": "fetched",
        "paper_id": "existing-com",
    }

    corpus = build_corpus_papers(
        hits=[],
        fetch_results=[],
        citations=[],
        existing_corpus={
            "version": 2,
            "papers": [existing_paper],
        },
    )

    assert len(corpus["papers"]) == 1
    assert corpus["papers"][0]["url"] == "https://existing.com"


@pytest.mark.asyncio
async def test_pipeline_build_outline(tmp_path):
    """build_outline creates a standard 5-section outline."""
    from app.agents.literature_turn_pipeline import build_outline

    papers = [
        {"title": "Paper A", "url": "https://a.com",
         "paper_id": "a-com", "subtopic_tags": []},
    ]

    outline = build_outline(
        papers=papers,
        search_aspects=[],
    )

    assert len(outline["sections"]) == 5
    assert outline["sections"][0]["title"] == "研究背景与问题定位"
