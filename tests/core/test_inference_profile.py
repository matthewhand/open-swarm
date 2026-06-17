"""Tests for inference-profile decoupling (intent -> backend matching)."""

from swarm.core import inference_profile as ip


def test_normalize_clamps_and_fills_defaults():
    n = ip.normalize({"intelligence": 2, "speed": -1})
    assert n["intelligence"] == 1.0  # clamped high
    assert n["speed"] == 0.0  # clamped low
    assert n["cost"] == 0.5  # missing -> default
    # garbage value -> default, not an error
    assert ip.normalize({"cost": "nope"})["cost"] == 0.5


CANDIDATES = {
    "smart": {"intelligence": 0.95, "speed": 0.4, "cost": 0.3},
    "fast_cheap": {"intelligence": 0.55, "speed": 0.95, "cost": 0.95},
}


def test_resolve_prefers_intelligence():
    assert ip.resolve({"intelligence": 1, "speed": 0, "cost": 0}, CANDIDATES) == "smart"


def test_resolve_prefers_speed_and_cost():
    assert ip.resolve({"intelligence": 0, "speed": 1, "cost": 1}, CANDIDATES) == "fast_cheap"


def test_rank_is_ordered_best_first_and_deterministic():
    ranked = ip.rank({"speed": 1, "cost": 1, "intelligence": 0}, CANDIDATES)
    assert [name for name, _ in ranked] == ["fast_cheap", "smart"]
    # equal scores tie-break by name
    flat = {"a": {"intelligence": 0.5}, "b": {"intelligence": 0.5}}
    assert [n for n, _ in ip.rank({"intelligence": 1}, flat)] == ["a", "b"]


def test_resolve_none_when_no_candidates():
    assert ip.resolve({"intelligence": 1}, {}) is None
