"""Tests for app.library.from_run — export sync."""
from app.library.from_run import _sync_exports
from app.library.store import LibraryStore


def test_sync_exports_writes_ref_list(tmp_path):
    lib = LibraryStore(data_dir=tmp_path)
    lib.put({
        "id": "a1", "display_index": 1, "title": "Paper One",
        "doi": "10.1/a", "url": "https://example.com/1",
        "citations": {"apa": "[1] A. Author (2024). Paper One. Nature."},
    })
    lib.put({
        "id": "b2", "display_index": 2, "title": "Paper Two",
        "doi": "10.2/b", "url": "https://example.com/2",
        "citations": {"apa": "[2] B. Author (2023). Paper Two. Science."},
    })
    _sync_exports(lib)

    ref_list_path = tmp_path / "refs" / "ref-list.txt"
    assert ref_list_path.exists()
    content = ref_list_path.read_text(encoding="utf-8")
    assert "[1] A. Author" in content
    assert "[2] B. Author" in content
