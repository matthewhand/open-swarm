"""Tests for /v1/team-rosters/ and /v1/team-agents/ (REQ-20).

The roster store is isolated from teams.json. Helpers are mocked so tests do
not write a real team_rosters.json unless they opt into a tmp_path.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from django.urls import resolve

from swarm.core.team_rosters import (
    DEFAULT_WIRES,
    normalize_member,
    normalize_roster,
    serialize_roster,
    slugify_roster_name,
)
from swarm.permissions import HasValidTokenOrSession
from swarm.views.team_rosters_api import TeamRosterDetailAPIView, TeamRostersAPIView


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def mock_rosters():
    return {
        "research-squad": {
            "id": "research-squad",
            "name": "Research Squad",
            "members": [
                {
                    "id": "jeeves",
                    "kind": "api",
                    "role": "default",
                    "source": "blueprint:jeeves",
                }
            ],
            "wires": {"handoff": True, "as_tool": True},
        }
    }


class TestRosterContractHelpers:
    def test_slugify(self):
        assert slugify_roster_name("Research Squad") == "research-squad"

    def test_member_defaults_source_and_role(self):
        member = normalize_member({"id": "grok", "kind": "cli"})
        assert member["role"] == "default"
        assert member["source"] == "cli:grok"

    def test_member_rejects_unknown_kind(self):
        with pytest.raises(ValueError, match="kind"):
            normalize_member({"id": "x", "kind": "blueprint"})

    def test_wires_default_both_on(self):
        roster = normalize_roster({"id": "t", "name": "T", "members": []})
        assert roster["wires"] == DEFAULT_WIRES

    def test_serialize_object_type(self):
        doc = serialize_roster(
            {"id": "t", "name": "T", "members": [], "wires": DEFAULT_WIRES}
        )
        assert doc["object"] == "team_roster"
        assert "llm_profile" not in doc


class TestTeamRosterRoutes:
    def test_roster_and_agent_urls_resolve(self):
        assert resolve("/v1/team-rosters/").url_name == "team-rosters-api"
        assert resolve("/v1/team-rosters").url_name == "team-rosters-api-no-slash"
        assert resolve("/v1/team-rosters/research-squad/").url_name == "team-rosters-api-detail"
        assert resolve("/v1/team-agents/").url_name == "team-agents-api"


class TestTeamRostersList:
    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_list_rosters(self, mock_load, api_client, mock_rosters):
        mock_load.return_value = mock_rosters
        response = api_client.get("/v1/team-rosters/")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["object"] == "list"
        assert len(body["data"]) == 1
        roster = body["data"][0]
        assert roster["object"] == "team_roster"
        assert roster["id"] == "research-squad"
        assert roster["members"][0]["kind"] == "api"
        assert roster["wires"] == {"handoff": True, "as_tool": True}
        assert "llm_profile" not in roster

    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_list_empty(self, mock_load, api_client):
        mock_load.return_value = {}
        response = api_client.get("/v1/team-rosters")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"object": "list", "data": []}


class TestTeamRostersCreate:
    @patch("swarm.views.team_rosters_api.upsert_roster")
    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_create_roster(self, mock_load, mock_upsert, api_client):
        mock_load.return_value = {}
        stored = {
            "id": "research-squad",
            "name": "Research Squad",
            "members": [
                {"id": "jeeves", "kind": "api", "role": "support", "source": "blueprint:jeeves"}
            ],
            "wires": {"handoff": True, "as_tool": False},
        }
        mock_upsert.return_value = stored

        response = api_client.post(
            "/v1/team-rosters/",
            data={
                "name": "Research Squad",
                "members": stored["members"],
                "wires": stored["wires"],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "research-squad"
        assert data["object"] == "team_roster"
        assert data["wires"]["as_tool"] is False
        mock_upsert.assert_called_once()
        written = mock_upsert.call_args[0][0]
        assert written["id"] == "research-squad"
        assert written["members"][0]["kind"] == "api"

    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_create_missing_name(self, mock_load, api_client):
        mock_load.return_value = {}
        response = api_client.post("/v1/team-rosters/", data={}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_create_duplicate(self, mock_load, api_client, mock_rosters):
        mock_load.return_value = mock_rosters
        response = api_client.post(
            "/v1/team-rosters/", data={"name": "Research Squad"}, format="json"
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    @patch("swarm.views.team_rosters_api.upsert_roster")
    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_create_rejects_bad_kind(self, mock_load, mock_upsert, api_client):
        mock_load.return_value = {}
        mock_upsert.side_effect = ValueError("Member kind must be one of api, cli, remote.")
        response = api_client.post(
            "/v1/team-rosters/",
            data={"name": "bad", "members": [{"id": "x", "kind": "blueprint"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_upsert.assert_called_once()


class TestTeamRosterDetail:
    @patch("swarm.views.team_rosters_api.get_roster")
    def test_get_roster(self, mock_get, api_client, mock_rosters):
        mock_get.return_value = mock_rosters["research-squad"]
        response = api_client.get("/v1/team-rosters/research-squad/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == "research-squad"

    @patch("swarm.views.team_rosters_api.get_roster")
    def test_get_missing(self, mock_get, api_client):
        mock_get.return_value = None
        response = api_client.get("/v1/team-rosters/missing/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("swarm.views.team_rosters_api.upsert_roster")
    @patch("swarm.views.team_rosters_api.get_roster")
    def test_put_roster(self, mock_get, mock_upsert, api_client, mock_rosters):
        mock_get.return_value = mock_rosters["research-squad"]
        updated = {
            **mock_rosters["research-squad"],
            "wires": {"handoff": False, "as_tool": True},
        }
        mock_upsert.return_value = updated
        response = api_client.put(
            "/v1/team-rosters/research-squad/",
            data={"wires": {"handoff": False, "as_tool": True}},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["wires"]["handoff"] is False

    @patch("swarm.views.team_rosters_api.delete_roster")
    def test_delete_roster(self, mock_delete, api_client):
        mock_delete.return_value = True
        response = api_client.delete("/v1/team-rosters/research-squad/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete.assert_called_once_with("research-squad")

    @patch("swarm.views.team_rosters_api.delete_roster")
    def test_delete_missing(self, mock_delete, api_client):
        mock_delete.return_value = False
        response = api_client.delete("/v1/team-rosters/missing/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTeamRostersIsolation:
    def test_store_path_is_not_teams_json(self, tmp_path, monkeypatch):
        from swarm.core import team_rosters as store

        monkeypatch.setattr(store, "get_user_config_dir_for_swarm", lambda: tmp_path)
        monkeypatch.setattr(store, "ensure_swarm_directories_exist", lambda: None)
        store.reset_team_rosters()
        path = store.team_rosters_path()
        assert path.name == "team_rosters.json"
        assert path != tmp_path / "teams.json"

        store._roster_registry = {}
        store.upsert_roster({"id": "alpha", "name": "Alpha", "members": []})
        assert (tmp_path / "team_rosters.json").exists()
        assert not (tmp_path / "teams.json").exists()
        store.reset_team_rosters()

    def test_teams_json_helpers_are_not_imported_by_roster_api(self):
        import swarm.views.team_rosters_api as api

        source = api.__file__
        text = open(source, encoding="utf-8").read()
        assert "load_dynamic_registry" not in text
        assert "register_dynamic_team" not in text
        assert "teams.json" in text  # documented as the other store


class TestTeamAgentsCatalog:
    @patch("swarm.views.team_rosters_api.list_available_team_agents")
    def test_lists_kinds(self, mock_list, api_client):
        mock_list.return_value = [
            {"id": "jeeves", "name": "Jeeves", "kind": "api", "source": "blueprint:jeeves", "placeholder": False},
            {"id": "grok", "name": "grok", "kind": "cli", "source": "cli:grok", "placeholder": False},
            {
                "id": "acp",
                "name": "ACP harness",
                "kind": "remote",
                "source": "placeholder:remote:acp",
                "placeholder": True,
            },
        ]
        response = api_client.get("/v1/team-agents/")
        assert response.status_code == status.HTTP_200_OK
        kinds = {row["kind"] for row in response.json()["data"]}
        assert kinds == {"api", "cli", "remote"}
        remotes = [row for row in response.json()["data"] if row["kind"] == "remote"]
        assert remotes[0]["placeholder"] is True


class TestTeamRostersAuth:
    def _authed_user(self):
        user = MagicMock()
        user.is_authenticated = True
        return user

    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_auth_disabled_allows_anonymous(self, mock_load, api_client):
        mock_load.return_value = {}
        with patch.object(TeamRostersAPIView, "permission_classes", []):
            response = api_client.get("/v1/team-rosters/")
        assert response.status_code == status.HTTP_200_OK

    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_auth_enabled_rejects_anonymous(self, mock_load, api_client):
        mock_load.return_value = {}
        with patch.object(TeamRostersAPIView, "permission_classes", [HasValidTokenOrSession]):
            response = api_client.get("/v1/team-rosters/")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    @override_settings(SWARM_API_KEY="test-token-123")
    @patch("swarm.views.team_rosters_api.load_team_rosters")
    def test_auth_enabled_accepts_bearer(self, mock_load, api_client):
        mock_load.return_value = {}
        api_client.credentials(HTTP_AUTHORIZATION="Bearer test-token-123")
        with patch.object(TeamRostersAPIView, "permission_classes", [HasValidTokenOrSession]):
            response = api_client.get("/v1/team-rosters/")
        assert response.status_code == status.HTTP_200_OK

    @patch("swarm.views.team_rosters_api.get_roster")
    def test_auth_enabled_rejects_anonymous_put(self, mock_get, api_client):
        mock_get.return_value = {"id": "x", "name": "x", "members": [], "wires": DEFAULT_WIRES}
        with patch.object(TeamRosterDetailAPIView, "permission_classes", [HasValidTokenOrSession]):
            response = api_client.put("/v1/team-rosters/x/", data={}, format="json")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
