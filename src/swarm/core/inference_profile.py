"""Decouple a blueprint's *intent* from a concrete inference backend.

A blueprint declares what kind of thinking it wants along a few axes, each a
0..1 **priority weight** — how much it cares — rather than naming a model:

    inference_profile = {"intelligence": 0.9, "speed": 0.2, "cost": 0.1}

Each available backend (a CLI or LLM profile) is tagged with 0..1 **capability**
scores on the same axes — how intelligent, how fast, how cheap it is:

    grok   -> {"intelligence": 0.9, "speed": 0.6, "cost": 0.5}
    gemini -> {"intelligence": 0.6, "speed": 0.9, "cost": 0.9}

``resolve`` then picks the available backend that best satisfies the blueprint's
priorities (a weighted dot product of priorities × capabilities). This keeps
blueprints portable: a blueprint says "I want smart", and it runs on whatever
the user has labelled smart on *their* host.

Axes (all 0..1, higher = more of the named good thing):
- ``intelligence`` — reasoning depth / quality.
- ``speed``        — responsiveness (higher = faster).
- ``cost``         — cheapness (higher = cheaper to run).
"""

from __future__ import annotations

from typing import Any

TRAITS: tuple[str, ...] = ("intelligence", "speed", "cost")
# Neutral default when an axis is unspecified: care/capability of 0.5.
_DEFAULT = 0.5


def normalize(profile: dict[str, Any] | None) -> dict[str, float]:
    """Clamp a partial trait dict to ``{trait: float in [0,1]}`` for every axis.

    Unknown keys are ignored; missing axes default to 0.5. Non-numeric values
    fall back to the default rather than raising.
    """
    profile = profile or {}
    out: dict[str, float] = {}
    for trait in TRAITS:
        try:
            v = float(profile.get(trait, _DEFAULT))
        except (TypeError, ValueError):
            v = _DEFAULT
        out[trait] = 0.0 if v < 0 else 1.0 if v > 1 else v
    return out


def score(desired: dict[str, Any] | None, capability: dict[str, Any] | None) -> float:
    """How well ``capability`` satisfies ``desired`` — weighted dot product.

    Each axis contributes ``priority * capability``; higher is better. With all
    priorities equal this just rewards the most capable backend overall.
    """
    d = normalize(desired)
    c = normalize(capability)
    return sum(d[t] * c[t] for t in TRAITS)


def rank(
    desired: dict[str, Any] | None, candidates: dict[str, dict[str, Any]]
) -> list[tuple[str, float]]:
    """Rank candidate backends (``{name: capability}``) best-first for ``desired``.

    Ties break by name for determinism.
    """
    scored = [(name, score(desired, cap)) for name, cap in candidates.items()]
    return sorted(scored, key=lambda kv: (-kv[1], kv[0]))


def resolve(
    desired: dict[str, Any] | None, candidates: dict[str, dict[str, Any]]
) -> str | None:
    """Pick the single best-matching backend name, or None if there are none."""
    ranked = rank(desired, candidates)
    return ranked[0][0] if ranked else None
