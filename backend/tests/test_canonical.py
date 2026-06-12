"""Tests for app.library.canonical — URL normalization and canonical key."""
from app.library.canonical import canonical_key, normalize_url


def test_normalize_url_basic():
    assert normalize_url("https://ARXIV.ORG/abs/2401.12345") == "https://arxiv.org/abs/2401.12345"


def test_normalize_url_strip_fragment():
    assert normalize_url("https://example.com/paper#section1") == "https://example.com/paper"


def test_normalize_url_strip_trailing_slash():
    assert normalize_url("https://example.com/paper/") == "https://example.com/paper"


def test_normalize_url_strip_utm():
    result = normalize_url(
        "https://example.com/paper?utm_source=google&id=1"
    )
    assert result == "https://example.com/paper?id=1"


def test_canonical_key_doi():
    key = canonical_key(doi="10.1145/1234567")
    assert key == "doi:10.1145/1234567"


def test_canonical_key_doi_lowercase():
    key = canonical_key(doi="10.1145/ABCDEF")
    assert key == "doi:10.1145/abcdef"


def test_canonical_key_url():
    key = canonical_key(url="https://arxiv.org/abs/2401.12345")
    assert key == "url:https://arxiv.org/abs/2401.12345"


def test_canonical_key_doi_priority():
    key = canonical_key(url="https://example.com", doi="10.1234/x")
    assert key.startswith("doi:")


def test_canonical_key_empty():
    assert canonical_key() == ""


def test_canonical_key_empty_strings():
    assert canonical_key(url="", doi="") == ""
