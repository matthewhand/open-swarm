"""Unit tests for swarm.core.team_rosters (composition store, not teams.json)."""

from unittest.mock import patch

from swarm.core.team_rosters import (
    PLACEHOLDER_REMOTE_AGENTS,
    list_available_team_agents,
    reset_team_rosters,
    team_rosters_path,
)


def test_path_is_team_rosters_json_not_teams_json():
    path = team_rosters_path()
    assert path.name == "team_rosters.json"
    assert "teams.json" not in str(path)


def test_catalog_includes_remote_placeholders_and_not_blueprint_kinds():
    with (
        patch(
            "swarm.core.team_rosters._blueprint_agents",
            return_value=[
                {
                    "id": "jeeves",
                    "name": "Jeeves",
                    "kind": "api",
                    "source": "blueprint:jeeves",
                    "placeholder": False,
                }
            ],
        ),
        patch(
            "swarm.core.team_rosters._cli_agents",
            return_value=[
                {
                    "id": "grok",
                    "name": "grok",
                    "kind": "cli",
                    "source": "cli:grok",
                    "placeholder": False,
                }
            ],
        ),
    ):
        agents = list_available_team_agents()
    kinds = {a["kind"] for a in agents}
    assert kinds == {"api", "cli", "remote"}
    remotes = [a for a in agents if a["kind"] == "remote"]
    assert {a["id"] for a in remotes} == {p["id"] for p in PLACEHOLDER_REMOTE_AGENTS}
    assert all(a["placeholder"] for a in remotes)
    assert all(a["kind"] != "blueprint" for a in agents)


def test_catalog_cli_failure_uses_placeholders():
    with (
        patch("swarm.core.team_rosters._blueprint_agents", return_value=[]),
        patch("swarm.core.team_rosters._cli_agents", side_effect=RuntimeError("no catalog")),
    ):
        agents = list_available_team_agents()
    clis = [a for a in agents if a["kind"] == "cli"]
    assert clis
    assert all(a.get("placeholder") for a in clis)


def test_reset_clears_cache():
    reset_team_rosters()
    from swarm.core import team_rosters as store

    assert store._roster_registry is None
