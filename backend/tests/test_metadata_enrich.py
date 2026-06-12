"""Tests for app.library.metadata_enrich."""
from app.library.metadata_enrich import _patch_from_crossref, _patch_from_openalex


def test_patch_from_crossref():
    data = {
        "message": {
            "is-referenced-by-count": 42,
            "references-count": 15,
            "reference": [{"DOI": "10.1/a"}, {"DOI": "10.2/b"}],
            "container-title": ["Nature"],
            "published-print": {"date-parts": [[2024, 3, 15]]},
        }
    }
    patch = _patch_from_crossref(data)
    assert patch["citation_count"] == 42
    assert patch["references_count"] == 15
    assert len(patch["references_preview"]) == 2
    assert patch["venue"] == "Nature"
    assert patch["year"] == "2024"


def test_patch_from_crossref_empty():
    patch = _patch_from_crossref({})
    assert patch["citation_count"] is None


def test_patch_from_openalex():
    data = {
        "doi": "10.1234/test",
        "cited_by_count": 100,
        "referenced_works_count": 30,
        "host_venue": {"display_name": "Science"},
        "publication_year": 2023,
    }
    patch = _patch_from_openalex(data)
    assert patch["doi"] == "10.1234/test"
    assert patch["citation_count"] == 100
    assert patch["venue"] == "Science"
    assert patch["year"] == "2023"


def test_patch_from_openalex_empty():
    patch = _patch_from_openalex({})
    assert patch["doi"] is None
