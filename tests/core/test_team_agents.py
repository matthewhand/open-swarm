"""GET /v1/team-agents/ palette — no secrets, no live host."""

from swarm.core.team_agents import list_team_agents


def test_list_team_agents_uses_injectables_and_marks_missing_cli():
    rows = list_team_agents(
        blueprint_ids=["jeeves"],
        cli_names=["grok", "missing-cli"],
        installed_clis=["grok"],
        remotes=[{"id": "hermes", "name": "Hermes"}],
    )
    by_id = {row["id"]: row for row in rows}
    assert by_id["jeeves"] == {
        "id": "jeeves",
        "name": "jeeves",
        "kind": "api",
        "source": "blueprint:jeeves",
        "placeholder": False,
    }
    assert by_id["grok"]["kind"] == "cli"
    assert by_id["grok"]["placeholder"] is False
    assert by_id["missing-cli"]["placeholder"] is True
    assert by_id["hermes"]["kind"] == "remote"
    blob = str(rows).lower()
    assert "api_key" not in blob
    assert "secret" not in blob
    assert ":8001" not in blob


def test_list_team_agents_omits_empty_remote_ids():
    rows = list_team_agents(
        blueprint_ids=[],
        cli_names=[],
        installed_clis=[],
        remotes=[{"id": "", "name": "nope"}, {"id": "omb", "name": "OpenMousBot"}],
    )
    assert [row["id"] for row in rows] == ["omb"]
