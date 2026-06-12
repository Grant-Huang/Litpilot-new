"""Tests for app.agents.content_pipeline — material assembly."""
from app.agents.content_pipeline import build_review_materials, build_qa_materials


def test_build_review_materials_basic():
    result = build_review_materials(
        search_hits=[{"title": "Paper A", "snippet": "About AI", "url": "https://a.com"}],
        fetch_texts=[{"url": "https://a.com", "text": "Full text of paper A about AI."}],
        citations=["[1] A. Author (2024). Paper A. Nature."],
    )
    assert "[web_search]" in result
    assert "[网页材料]" in result
    assert "[Citations]" in result
    assert "Paper A" in result
    assert "Full text" in result


def test_build_review_materials_empty():
    result = build_review_materials(
        search_hits=[], fetch_texts=[], citations=[]
    )
    assert result == ""


def test_build_review_materials_truncates_long_text():
    long_text = "x" * 20000
    result = build_review_materials(
        search_hits=[],
        fetch_texts=[{"url": "https://a.com", "text": long_text}],
        citations=[],
        max_source_chars=1000,
    )
    # Each source should be truncated
    assert len(result) < 20000


def test_build_qa_materials_includes_prior_review():
    result = build_qa_materials(
        prior_review="# Existing Review\n\nSome review content here.",
        fetch_texts=[{"url": "https://a.com", "text": "Paper text."}],
        citations=["[1] Test."],
    )
    assert "[已生成综述]" in result
    assert "Existing Review" in result


def test_build_qa_materials_no_prior_review():
    result = build_qa_materials(
        prior_review="",
        fetch_texts=[],
        citations=[],
    )
    assert "[已生成综述]" not in result
