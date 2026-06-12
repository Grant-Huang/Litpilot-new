"""Tests for app.library.upsert_citation."""
import pytest

from app.library.store import LibraryStore
from app.library.upsert_citation import upsert_from_citation


class FakeCitationRecord:
    def __init__(self, **kwargs):
        self.title = kwargs.get("title", "Test Paper")
        self.authors = kwargs.get("authors", "A. Author")
        self.year = kwargs.get("year", "2024")
        self.venue = kwargs.get("venue", "Nature")
        self.doi = kwargs.get("doi", "10.1234/test")
        self.url = kwargs.get("url", "https://example.com/paper1")
        self.abstract = kwargs.get("abstract", "An abstract.")
        self.publisher = kwargs.get("publisher", "")
        self.success = kwargs.get("success", True)
        self.error = kwargs.get("error", "")

    def to_apa(self, index):
        doi_part = f"https://doi.org/{self.doi}" if self.doi else ""
        return (f"[{index}] {self.authors} ({self.year}). "
                f"{self.title}. {self.venue}. {doi_part}")


@pytest.fixture
def lib(tmp_path):
    return LibraryStore(data_dir=tmp_path)


def test_insert_new(lib):
    rec = FakeCitationRecord()
    result = upsert_from_citation(rec, lib=lib, citation_format="apa",
                                  session_id="sess1", session_title="Test")
    assert result is not None
    assert result["display_index"] == 1
    assert result["title"] == "Test Paper"
    assert "apa" in result["citations"]


def test_insert_failed_record_skipped(lib):
    rec = FakeCitationRecord(success=False, error="insufficient metadata")
    result = upsert_from_citation(rec, lib=lib)
    assert result is None
    assert lib.all_items() == []


def test_dedup_by_doi(lib):
    rec1 = FakeCitationRecord(doi="10.1234/dup", title="Original")
    upsert_from_citation(rec1, lib=lib, session_id="s1")
    rec2 = FakeCitationRecord(doi="10.1234/dup", title="Updated Title",
                              abstract="New abstract")
    result = upsert_from_citation(rec2, lib=lib, session_id="s2")
    assert result is not None
    items = lib.all_items()
    assert len(items) == 1
    assert items[0]["title"] == "Updated Title"


def test_dedup_by_url(lib):
    rec1 = FakeCitationRecord(doi="", url="https://example.com/same")
    upsert_from_citation(rec1, lib=lib, session_id="s1")
    rec2 = FakeCitationRecord(
        doi="", url="https://example.com/same", title="New Title"
    )
    upsert_from_citation(rec2, lib=lib, session_id="s2")
    items = lib.all_items()
    assert len(items) == 1


def test_provenance_tracking(lib):
    rec = FakeCitationRecord()
    result = upsert_from_citation(rec, lib=lib, session_id="s1",
                                  session_title="My Session")
    prov = result.get("provenance", [])
    assert len(prov) == 1
    assert prov[0]["session_id"] == "s1"
    assert prov[0]["session_title"] == "My Session"


def test_provenance_merge_on_dedup(lib):
    rec1 = FakeCitationRecord()
    upsert_from_citation(rec1, lib=lib, session_id="s1", session_title="First")
    rec2 = FakeCitationRecord()
    result = upsert_from_citation(rec2, lib=lib, session_id="s2",
                                  session_title="Second")
    prov = result.get("provenance", [])
    assert len(prov) == 2


def test_enrich_patch_applied(lib):
    rec = FakeCitationRecord()
    patch = {
        "citation_count": 42,
        "references_count": 15,
        "references_preview": [{"title": "Ref1", "year": "2020"}],
    }
    result = upsert_from_citation(rec, lib=lib, enrich_patch=patch)
    assert result["citation_count"] == 42
    assert result["references_count"] == 15


def test_only_apa_citation(lib):
    rec = FakeCitationRecord()
    result = upsert_from_citation(rec, lib=lib, citation_format="apa")
    assert "apa" in result["citations"]
    assert "acm" not in result["citations"]
