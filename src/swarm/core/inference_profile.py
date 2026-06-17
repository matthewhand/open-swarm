"""Decouple a blueprint's *intent* from a concrete inference backend.

A blueprint declares the *kind of inference it wants* as a target along a few
0..1 axes, naming only the axes it cares about:

    inference_profile = {"intelligence": 1.0}          # "I want the smartest"
    inference_profile = {"speed": 0.9, "cost": 0.9}    # "fast and cheap"
    inference_profile = {"intelligence": 0.6, "speed": 0.6, "cost": 0.6}  # balanced

Each available backend (a CLI or LLM profile) is tagged with 0..1 **capability**
scores on the same axes. ``resolve`` picks the backend whose capabilities are
**closest** to the requested target (Euclidean distance over the axes the
blueprint specified — unspecified axes are "don't care" and never penalize). So
"balanced" lands on a genuine all-rounder, and a single-axis target like
``{"intelligence": 1.0}`` lands on the most intelligent backend without caring
how fast or cheap it happens to be.

Axes (all 0..1, higher = more of the named good thing):
- ``intelligence`` — reasoning depth / quality.
- ``speed``        — responsiveness (higher = faster).
- ``cost``         — cheapness (higher = cheaper to run).
"""

from __future__ import annotations

import math
from typing import Any

TRAITS: tuple[str, ...] = ("intelligence", "speed", "cost")
# Neutral default for a backend that doesn't declare an axis.
_DEFAULT = 0.5


def _clamp(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _DEFAULT
    return 0.0 if f < 0 else 1.0 if f > 1 else f


def normalize(profile: dict[str, Any] | None) -> dict[str, float]:
    """Clamp a trait dict to ``{trait: float in [0,1]}`` for every known axis.

    Missing axes default to 0.5. Used for **capability** vectors (backends),
    which are scored on all axes.
    """
    profile = profile or {}
    return {t: _clamp(profile.get(t, _DEFAULT)) for t in TRAITS}


def _target_axes(desired: dict[str, Any] | None) -> dict[str, float]:
    """The axes a blueprint actually asked for (known axes only), clamped.

    Unspecified axes are omitted — they are "don't care" and excluded from the
    distance, so a backend is never penalised for an axis the blueprint ignored.
    """
    desired = desired or {}
    return {t: _clamp(desired[t]) for t in TRAITS if t in desired}


def score(desired: dict[str, Any] | None, capability: dict[str, Any] | None) -> float:
    """Match quality of ``capability`` for ``desired`` — higher is better.

    Returns the negated Euclidean distance to the target over the requested
    axes, so the closest backend scores highest. With no axes requested every
    backend ties at 0.
    """
    target = _target_axes(desired)
    cap = normalize(capability)
    dist = math.sqrt(sum((target[a] - cap[a]) ** 2 for a in target))
    return -dist


def rank(
    desired: dict[str, Any] | None, candidates: dict[str, dict[str, Any]]
) -> list[tuple[str, float]]:
    """Rank candidate backends (``{name: capability}``) best-first for ``desired``.

    Ties (including "no axes requested") break by name for determinism.
    """
    scored = [(name, score(desired, cap)) for name, cap in candidates.items()]
    return sorted(scored, key=lambda kv: (-kv[1], kv[0]))


def resolve(
    desired: dict[str, Any] | None, candidates: dict[str, dict[str, Any]]
) -> str | None:
    """Pick the single closest-matching backend name, or None if there are none."""
    ranked = rank(desired, candidates)
    return ranked[0][0] if ranked else None
