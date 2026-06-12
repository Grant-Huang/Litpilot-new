"""Tests for app.agents.literature_router — intent routing (3 intents)."""
from app.agents.literature_router import route_intent, _contains_url


def test_first_turn_new_topic():
    assert route_intent(
        user_turns=1,
        message="AI in healthcare",
        fetch_urls=[],
        has_corpus=False,
    ) == "new_topic"


def test_first_turn_zero():
    assert route_intent(
        user_turns=0,
        message="quantum computing",
        fetch_urls=[],
        has_corpus=False,
    ) == "new_topic"


def test_second_turn_with_urls():
    assert route_intent(
        user_turns=2,
        message="add these papers",
        fetch_urls=["https://arxiv.org/abs/2401.12345"],
        has_corpus=True,
    ) == "append_urls"


def test_second_turn_url_in_message():
    assert route_intent(
        user_turns=2,
        message="check https://example.com/paper",
        fetch_urls=[],
        has_corpus=True,
    ) == "append_urls"


def test_second_turn_no_url_corpus_exists():
    assert route_intent(
        user_turns=2,
        message="what did Smith find?",
        fetch_urls=[],
        has_corpus=True,
    ) == "query_corpus"


def test_second_turn_no_url_no_corpus():
    assert route_intent(
        user_turns=2,
        message="tell me about AI",
        fetch_urls=[],
        has_corpus=False,
    ) == "query_corpus"


def test_has_corpus_never_new_topic_after_first():
    result = route_intent(
        user_turns=3,
        message="new topic please",
        fetch_urls=[],
        has_corpus=True,
    )
    assert result == "query_corpus"


def test_contains_url():
    assert _contains_url("see https://arxiv.org/abs/2401.12345")
    assert _contains_url("http://example.com")
    assert not _contains_url("no link here")
    assert not _contains_url("")


def test_turns_2_with_fetch_urls_but_empty():
    assert route_intent(
        user_turns=2,
        message="something",
        fetch_urls=[],
        has_corpus=True,
    ) == "query_corpus"


def test_turns_2_with_fetch_urls():
    assert route_intent(
        user_turns=2,
        message="add these",
        fetch_urls=["https://a.com"],
        has_corpus=True,
    ) == "append_urls"
