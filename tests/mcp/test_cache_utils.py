"""Unit tests for swarm.extensions.mcp.cache_utils.

DummyCache is the null-cache fallback used when Django's cache is unavailable.
Its whole point is to *never* store anything while still satisfying the
get/set cache interface — these tests pin that no-op contract so a future
change can't silently turn it into a real (and wrong) cache. get_cache() is
checked only for the cache-like duck type it must always return.
"""

from swarm.extensions.mcp.cache_utils import DummyCache, get_cache


def test_dummy_cache_get_returns_default_when_unset():
    cache = DummyCache()
    assert cache.get("missing") is None
    assert cache.get("missing", "fallback") == "fallback"
    assert cache.get("missing", default=42) == 42


def test_dummy_cache_set_is_a_noop_and_does_not_store():
    cache = DummyCache()
    # set must accept value (+ optional timeout) and return None.
    assert cache.set("k", "v") is None
    assert cache.set("k", "v", timeout=30) is None
    # A null cache never serves what was "set" — get still yields the default.
    assert cache.get("k") is None
    assert cache.get("k", "still-default") == "still-default"


def test_get_cache_returns_a_cache_like_object():
    cache = get_cache()
    assert hasattr(cache, "get")
    assert hasattr(cache, "set")
    # Whatever backend is returned, the get/set duck type must be callable.
    assert callable(cache.get)
    assert callable(cache.set)
