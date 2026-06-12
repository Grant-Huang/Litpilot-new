"""Tests for app.agents.literature_turn_finalize — finalization."""
import pytest

from app.agents.literature_turn_finalize import finalize_turn
from app.storage.file_store import FileStore


def _make_store(tmp_path):
    return FileStore(data_dir=tmp_path)


@pytest.mark.asyncio
async def test_finalize_saves_review_version(tmp_path):
    """finalize_turn saves review as v1."""
    store = _make_store(tmp_path)
    session = store.create_session()

    await finalize_turn(
        session_id=session["id"],
        store=store,
        intent="new_topic",
        review_text="# Review\n\nContent here.",
        matrix_text="| Dim | Paper |\n|---|---|",
        corpus={"version": 1, "papers": [
            {"url": "https://a.com", "title": "Paper A",
             "paper_id": "a-com", "subtopic_tags": []},
        ]},
        outline={"sections": [], "subtopics": []},
        citations=["[1] Author (2024). Title. Journal."],
    )

    # Check review saved
    versions = store.list_review_versions(session["id"])
    assert "v1" in versions

    # Check corpus saved
    corpus = store.read_corpus(session["id"])
    assert len(corpus.get("papers", [])) == 1


@pytest.mark.asyncio
async def test_finalize_increments_version(tmp_path):
    """finalize_turn increments review version v1→v2."""
    store = _make_store(tmp_path)
    session = store.create_session()

    # First save v1
    await finalize_turn(
        session_id=session["id"],
        store=store,
        intent="new_topic",
        review_text="# Review v1",
        matrix_text="",
        corpus={"version": 1, "papers": []},
        outline={"sections": [], "subtopics": []},
        citations=[],
    )

    # Second save v2
    await finalize_turn(
        session_id=session["id"],
        store=store,
        intent="append_urls",
        review_text="# Review v2",
        matrix_text="",
        corpus={"version": 2, "papers": []},
        outline={"sections": [], "subtopics": []},
        citations=[],
    )

    versions = store.list_review_versions(session["id"])
    assert "v1" in versions
    assert "v2" in versions


@pytest.mark.asyncio
async def test_finalize_qa_no_review_save(tmp_path):
    """finalize_turn for query_corpus does not save review."""
    store = _make_store(tmp_path)
    session = store.create_session()

    await finalize_turn(
        session_id=session["id"],
        store=store,
        intent="query_corpus",
        review_text="",
        matrix_text="",
        corpus=None,
        outline=None,
        citations=[],
    )

    versions = store.list_review_versions(session["id"])
    assert versions == []


@pytest.mark.asyncio
async def test_finalize_saves_matrix(tmp_path):
    """finalize_turn saves matrix if provided."""
    store = _make_store(tmp_path)
    session = store.create_session()

    await finalize_turn(
        session_id=session["id"],
        store=store,
        intent="new_topic",
        review_text="# Review",
        matrix_text="| Dim | Paper |\n|---|---|",
        corpus={"version": 1, "papers": []},
        outline={"sections": [], "subtopics": []},
        citations=[],
    )

    matrix = store.read_matrix(session["id"])
    assert matrix is not None
    assert "Dim" in matrix


@pytest.mark.asyncio
async def test_finalize_saves_outline(tmp_path):
    """finalize_turn saves outline."""
    store = _make_store(tmp_path)
    session = store.create_session()

    outline_data = {
        "sections": [{"id": "s1", "title": "Background"}],
        "subtopics": [],
    }

    await finalize_turn(
        session_id=session["id"],
        store=store,
        intent="new_topic",
        review_text="# Review",
        matrix_text="",
        corpus={"version": 1, "papers": []},
        outline=outline_data,
        citations=[],
    )

    saved = store.read_outline(session["id"])
    assert saved is not None
    assert len(saved.get("sections", [])) == 1
