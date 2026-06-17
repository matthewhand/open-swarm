"""Tests for inference-profile decoupling (intent -> backend, distance-from-ideal)."""

from swarm.core import inference_profile as ip


def test_normalize_clamps_and_fills_defaults():
    n = ip.normalize({"intelligence": 2, "speed": -1})
    assert n["intelligence"] == 1.0  # clamped high
    assert n["speed"] == 0.0  # clamped low
    assert n["cost"] == 0.5  # missing -> default
    assert ip.normalize({"cost": "nope"})["cost"] == 0.5  # garbage -> default


CANDIDATES = {
    "smart": {"intelligence": 0.95, "speed": 0.40, "cost": 0.30},
    "fast_cheap": {"intelligence": 0.55, "speed": 0.95, "cost": 0.95},
    "allrounder": {"intelligence": 0.60, "speed": 0.60, "cost": 0.60},
}


def test_single_axis_target_ignores_other_axes():
    # "I want the smartest" — speed/cost unspecified, so not penalised.
    assert ip.resolve({"intelligence": 1.0}, CANDIDATES) == "smart"


def test_fast_cheap_target():
    assert ip.resolve({"speed": 1.0, "cost": 1.0}, CANDIDATES) == "fast_cheap"


def test_balanced_picks_the_allrounder_not_highest_aggregate():
    # The whole point of distance-from-ideal: balanced -> the generalist,
    # not whoever has the highest total capability.
    assert ip.resolve({"intelligence": 0.6, "speed": 0.6, "cost": 0.6}, CANDIDATES) == "allrounder"


def test_rank_is_ordered_and_deterministic():
    ranked = ip.rank({"speed": 1.0, "cost": 1.0}, CANDIDATES)
    assert ranked[0][0] == "fast_cheap"
    # equal distance -> tie-break by name
    flat = {"a": {"intelligence": 0.5}, "b": {"intelligence": 0.5}}
    assert [n for n, _ in ip.rank({"intelligence": 0.5}, flat)] == ["a", "b"]


def test_unspecified_axes_do_not_penalize():
    # A backend that is also fast/cheap is not punished for a pure-intelligence ask.
    cands = {
        "smart_slow": {"intelligence": 0.9, "speed": 0.1, "cost": 0.1},
        "smart_fast": {"intelligence": 0.9, "speed": 0.9, "cost": 0.9},
    }
    # Both equally close on intelligence -> tie by name (neither penalised on speed/cost).
    assert ip.resolve({"intelligence": 0.9}, cands) == "smart_fast"  # name order: f < s


def test_resolve_none_when_no_candidates():
    assert ip.resolve({"intelligence": 1}, {}) is None


def test_resolve_none_when_no_scorable_axis():
    # Empty or all-unknown-axis target -> decline (caller uses its default),
    # rather than silently picking the alphabetically-first backend.
    assert ip.resolve({}, CANDIDATES) is None
    assert ip.resolve({"bogus": 1.0}, CANDIDATES) is None
