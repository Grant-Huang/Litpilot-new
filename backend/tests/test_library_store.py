"""Tests for app.library.store."""
import pytest

from app.library.store import LibraryStore


@pytest.fixture
def store(tmp_path):
    return LibraryStore(data_dir=tmp_path)


def test_empty_store(store):
    items = store.all_items()
    assert items == []


def test_put_and_get(store):
    item = {"id": "abcd1234", "display_index": 1, "title": "Test Paper",
            "url": "https://example.com", "doi": "", "authors": [],
            "citations": {"apa": "[1] Test Paper"}}
    result = store.put(item)
    assert result["display_index"] == 1

    got = store.get("abcd1234")
    assert got["title"] == "Test Paper"


def test_get_not_found(store):
    assert store.get("nonexistent") is None


def test_get_by_key(store):
    item = {"id": "a1", "display_index": 1, "title": "T1",
            "url": "https://example.com/paper1", "doi": "10.1234/x",
            "authors": [], "citations": {}}
    store.put(item)
    assert store.get_by_key("doi:10.1234/x") is not None
    assert store.get_by_key("url:https://example.com/paper1") is not None


def test_all_items_sorted_by_index(store):
    store.put({"id": "b", "display_index": 2, "title": "Second"})
    store.put({"id": "a", "display_index": 1, "title": "First"})
    items = store.all_items()
    assert items[0]["display_index"] == 1
    assert items[1]["display_index"] == 2


def test_alloc_display_index(store):
    assert store.alloc_display_index() == 1
    assert store.alloc_display_index() == 2
    assert store.alloc_display_index() == 3


def test_alloc_display_index_after_put(store):
    store.put({"id": "x", "display_index": 5, "title": "T"})
    assert store.alloc_display_index() == 6


def test_delete(store):
    store.put({"id": "d1", "display_index": 1, "title": "Delete Me"})
    assert store.delete("d1") is True
    assert store.get("d1") is None
    assert store.delete("d1") is False


def test_upsert_updates_existing(store):
    store.put({"id": "u1", "display_index": 1, "title": "Original",
               "doi": "10.1234/y", "authors": []})
    store.put({"id": "u1", "display_index": 1, "title": "Updated",
               "doi": "10.1234/y", "authors": ["A. Author"]})
    got = store.get("u1")
    assert got["title"] == "Updated"
    assert got["authors"] == ["A. Author"]
