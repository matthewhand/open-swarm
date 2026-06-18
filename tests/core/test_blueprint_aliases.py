"""Canonical swarm_* aliases for the cli_* orchestration patterns."""

from __future__ import annotations

from pathlib import Path

from swarm.core.blueprint_discovery import (
    BLUEPRINT_ALIASES,
    apply_blueprint_aliases,
    discover_blueprints,
)


def _discovered():
    return apply_blueprint_aliases(discover_blueprints(str(Path("src/swarm/blueprints").resolve())))


def test_every_alias_resolves_to_its_target_class():
    d = _discovered()
    for alias, target in BLUEPRINT_ALIASES.items():
        assert alias in d, f"{alias} not registered"
        assert target in d, f"{target} (target of {alias}) missing"
        assert d[alias]["class_type"] is d[target]["class_type"]


def test_alias_advertises_canonical_name():
    d = _discovered()
    assert d["swarm_recurse"]["metadata"]["name"] == "swarm_recurse"
    assert d["swarm_ensemble"]["metadata"]["name"] == "swarm_ensemble"


def test_cli_names_still_present():
    d = _discovered()
    for cli_name in ("cli_agent", "cli_fusion", "cli_recurse", "cli_map"):
        assert cli_name in d  # back-compat preserved


def test_cli_agent_has_no_swarm_alias():
    # cli_agent is the CLI primitive, intentionally not aliased to swarm_.
    assert "swarm_agent" not in BLUEPRINT_ALIASES


def test_aliases_are_idempotent():
    d = apply_blueprint_aliases(_discovered())  # apply twice
    assert d["swarm_recurse"]["class_type"] is d["cli_recurse"]["class_type"]
