"""Tests for app.storage.file_store."""
import pytest

from app.storage.file_store import FileStore


@pytest.fixture
def store(tmp_path):
    return FileStore(data_dir=tmp_path)


def test_create_and_list_sessions(store):
    s = store.create_session("Test Session")
    assert s["title"] == "Test Session"
    assert s["id"]
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["id"] == s["id"]


def test_get_meta(store):
    s = store.create_session("My Session")
    meta = store.get_meta(s["id"])
    assert meta["title"] == "My Session"


def test_get_meta_not_found(store):
    assert store.get_meta("nonexistent") is None


def test_update_meta(store):
    s = store.create_session()
    store.update_meta(s["id"], title="Renamed", pinned=True)
    meta = store.get_meta(s["id"])
    assert meta["title"] == "Renamed"
    assert meta["pinned"] is True


def test_delete_session(store):
    s = store.create_session()
    store.delete_session(s["id"])
    assert store.list_sessions() == []
    assert store.get_meta(s["id"]) is None


def test_append_and_read_messages(store):
    s = store.create_session()
    user_msg = {"role": "user", "content": "Hello", "session_id": s["id"]}
    store.append_message(s["id"], user_msg)
    assistant_msg = {"role": "assistant", "content": "Hi", "session_id": s["id"]}
    store.append_message(s["id"], assistant_msg)
    msgs = store.read_messages(s["id"])
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "Hi"


def test_corpus_read_write(store):
    s = store.create_session()
    corpus = {"version": 2, "papers": [{"url": "https://example.com"}]}
    store.write_corpus(s["id"], corpus)
    result = store.read_corpus(s["id"])
    assert result["papers"][0]["url"] == "https://example.com"


def test_corpus_not_found(store):
    s = store.create_session()
    assert store.read_corpus(s["id"]) == {"version": 2, "papers": []}


def test_review_versioning(store):
    s = store.create_session()
    v1 = store.write_review(s["id"], "# Review v1\n\nContent 1")
    assert v1 == "v1"
    v2 = store.write_review(s["id"], "# Review v2\n\nContent 2")
    assert v2 == "v2"

    versions = store.list_review_versions(s["id"])
    assert versions == ["v1", "v2"]

    latest = store.read_review(s["id"])
    assert "v2" in latest

    v1_text = store.read_review(s["id"], version="v1")
    assert "v1" in v1_text


def test_review_no_letter_suffix(store):
    s = store.create_session()
    store.write_review(s["id"], "First")
    store.write_review(s["id"], "Second")
    store.write_review(s["id"], "Third")
    versions = store.list_review_versions(s["id"])
    assert versions == ["v1", "v2", "v3"]


def test_matrix_read_write(store):
    s = store.create_session()
    store.write_matrix(s["id"], "| Col1 | Col2 |\n|---|---|")
    result = store.read_matrix(s["id"])
    assert "Col1" in result


def test_outline_read_write(store):
    s = store.create_session()
    outline = {"version": 1, "topic": "AI MOM", "sections": []}
    store.write_outline(s["id"], outline)
    result = store.read_outline(s["id"])
    assert result["topic"] == "AI MOM"


def test_outline_not_found(store):
    s = store.create_session()
    assert store.read_outline(s["id"]) is None


def test_list_sessions_order(store):
    s1 = store.create_session("A")
    s2 = store.create_session("B")
    store.update_meta(s2["id"], pinned=True)
    sessions = store.list_sessions()
    assert sessions[0]["id"] == s2["id"]
    assert sessions[1]["id"] == s1["id"]
