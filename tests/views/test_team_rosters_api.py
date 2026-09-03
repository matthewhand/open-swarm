"""GET /v1/team-rosters/ — multi-agent rosters (REQ-23), not /v1/teams aliases."""

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from swarm.views.team_rosters import DEMO_TEAM_ROSTER, TeamRostersAPIView


@pytest.fixture
def api_client():
    return APIClient()


class TestTeamRostersListView:
    @patch("swarm.views.team_rosters.load_team_rosters")
    def test_list_rosters_shape(self, mock_load, api_client):
        mock_load.return_value = [
            {
                "id": "demo-council",
                "object": "team_roster",
                "name": "Demo Council",
                "description": "Example",
                "members": [
                    {
                        "id": "planner",
                        "name": "Planner",
                        "kind": "coordinator",
                        "role": "coordinator",
                    }
                ],
            }
        ]

        response = api_client.get("/v1/team-rosters/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["object"] == "list"
        assert len(payload["data"]) == 1
        team = payload["data"][0]
        assert team["object"] == "team_roster"
        assert team["id"] == "demo-council"
        assert "llm_profile" not in team
        assert team["members"][0]["id"] == "planner"

    @patch("swarm.views.team_rosters.load_team_rosters")
    def test_empty_member_roster_is_kept(self, mock_load, api_client):
        mock_load.return_value = [
            {
                "id": "empty-squad",
                "object": "team_roster",
                "name": "Empty Squad",
                "description": "",
                "members": [],
            }
        ]

        response = api_client.get("/v1/team-rosters/")

        assert response.status_code == status.HTTP_200_OK
        team = response.json()["data"][0]
        assert team["id"] == "empty-squad"
        assert team["members"] == []

    def test_missing_file_falls_back_to_demo(self, api_client, tmp_path, monkeypatch):
        from swarm.views import team_rosters as module

        monkeypatch.setattr(module, "_user_rosters_path", lambda: tmp_path / "missing.json")
        monkeypatch.setattr(module, "PACKAGED_ROSTERS_PATH", tmp_path / "also-missing.json")

        response = api_client.get("/v1/team-rosters/")

        assert response.status_code == status.HTTP_200_OK
        ids = [row["id"] for row in response.json()["data"]]
        assert DEMO_TEAM_ROSTER["id"] in ids

    def test_does_not_read_llm_alias_teams_json(self, api_client):
        with patch("swarm.views.utils.load_dynamic_registry") as mock_alias:
            mock_alias.return_value = {"alias": {"id": "alias", "llm_profile": "default"}}
            response = api_client.get("/v1/team-rosters/")
        mock_alias.assert_not_called()
        assert response.status_code == status.HTTP_200_OK
        for team in response.json()["data"]:
            assert team.get("object") == "team_roster"
            assert "llm_profile" not in team

    def test_permissions_match_teams_api(self):
        from swarm.views.teams_api import TEAMS_API_PERMISSIONS

        assert TeamRostersAPIView.permission_classes == TEAMS_API_PERMISSIONS
