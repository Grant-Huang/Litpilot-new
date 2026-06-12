"""Tests for app.config.personal_config."""
from app.config.personal_config import get_preferences, put_preferences


def test_get_preferences_returns_empty():
    assert get_preferences() == {}


def test_put_preferences_returns_empty():
    assert put_preferences({"citation_format": "apa"}) == {}
    assert get_preferences() == {}
