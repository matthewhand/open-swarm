"""API tests for /v1/team-rosters/ (composition, not LLM aliases)."""

import pytest
from rest_framework.test import APIClient

from swarm.core.team_rosters import reset_team_rosters


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _isolate_rosters(tmp_path, monkeypatch):
    from swarm.core import team_rosters as store

    cfg = tmp_path / "cfg"
    cfg.mkdir()
    monkeypatch.setattr(store, "get_user_config_dir_for_swarm", lambda: cfg)
    monkeypatch.setattr(store, "ensure_swarm_directories_exist", lambda: None)
    reset_team_rosters()
    yield
    reset_team_rosters()


def test_create_and_list_nested_roster_with_cos(api_client):
    response = api_client.post(
        "/v1/team-rosters/",
        {
            "name": "Office",
            "members": [
                {"id": "cos", "kind": "api", "role": "cos", "source": "blueprint:cos"},
                {"id": "research", "kind": "team", "team_id": "research", "role": "default"},
                {"id": "w3p1", "kind": "herdr", "role": "default"},
            ],
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["object"] == "team_roster"
    assert body["id"] == "office"
    roles = {m["id"]: m for m in body["members"]}
    assert roles["cos"]["role"] == "chief_of_staff"
    assert roles["research"]["kind"] == "team"
    assert roles["research"]["team_id"] == "research"
    assert roles["w3p1"]["kind"] == "herdr"

    listed = api_client.get("/v1/team-rosters/")
    assert listed.status_code == 200
    assert listed.json()["object"] == "list"
    assert listed.json()["data"][0]["id"] == "office"


def test_does_not_write_teams_json_aliases(api_client, monkeypatch):
    """Roster POST must not touch the LLM-alias registry."""
    called = {"register": False}

    def boom(*_a, **_k):
        called["register"] = True
        raise AssertionError("must not register a dynamic team alias")

    monkeypatch.setattr("swarm.views.utils.register_dynamic_team", boom)
    response = api_client.post(
        "/v1/team-rosters/",
        {"name": "solo", "members": [{"id": "a", "kind": "api", "role": "default"}]},
        format="json",
    )
    assert response.status_code == 201
    assert called["register"] is False


def test_create_roster_with_blueprint_id_attaches_personas(api_client):
    response = api_client.post(
        "/v1/team-rosters/",
        {
            "name": "Dev squad",
            "blueprint_id": "software_dev",
            "members": [{"id": "cos", "kind": "api", "role": "cos"}],
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["blueprint_id"] == "software_dev"
    assert body["persona_count"] == 3
    assert [p["name"] for p in body["personas"]] == [
        "engineer",
        "skeptic",
        "coding-requirements-gate",
    ]


def test_create_roster_with_remote_members(api_client):
    """PR #318: POST /v1/team-rosters/ accepts Hermes/OMB/Rakazo as kind=remote."""
    response = api_client.post(
        "/v1/team-rosters/",
        {
            "name": "Harness",
            "members": [
                {"id": "hermes", "kind": "remote", "role": "default"},
                {"id": "omb", "kind": "remote", "role": "default"},
                {"id": "rakazo", "kind": "remote", "role": "default"},
            ],
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["object"] == "team_roster"
    kinds = {m["id"]: m["kind"] for m in body["members"]}
    assert kinds == {"hermes": "remote", "omb": "remote", "rakazo": "remote"}
    listed = api_client.get("/v1/team-rosters/")
    assert listed.status_code == 200
    assert listed.json()["data"][0]["id"] == "harness"
