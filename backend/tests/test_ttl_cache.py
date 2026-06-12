"""Tests for app.agents.ttl_cache."""
import time

from app.agents.ttl_cache import TTLCache, normalize_cache_key


def test_cache_set_get():
    c = TTLCache(ttl_sec=60)
    c.set("k1", "v1")
    assert c.get("k1") == "v1"


def test_cache_miss():
    c = TTLCache(ttl_sec=60)
    assert c.get("nonexistent") is None


def test_cache_expired():
    c = TTLCache(ttl_sec=0.1)
    c.set("k1", "v1")
    assert c.get("k1") == "v1"
    time.sleep(0.15)
    assert c.get("k1") is None


def test_cache_overwrite():
    c = TTLCache(ttl_sec=60)
    c.set("k1", "v1")
    c.set("k1", "v2")
    assert c.get("k1") == "v2"


def test_cache_maxsize_eviction():
    c = TTLCache(ttl_sec=60, maxsize=2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_normalize_cache_key_deterministic():
    k1 = normalize_cache_key("multi_academic", "graph neural network", {"max_results": 20})
    k2 = normalize_cache_key("multi_academic", "graph neural network", {"max_results": 20})
    assert k1 == k2


def test_normalize_cache_key_different_args():
    k1 = normalize_cache_key("native", "q1")
    k2 = normalize_cache_key("native", "q2")
    assert k1 != k2


def test_normalize_cache_key_extra_order():
    k1 = normalize_cache_key("p", "q", {"a": 1, "b": 2})
    k2 = normalize_cache_key("p", "q", {"b": 2, "a": 1})
    assert k1 == k2
