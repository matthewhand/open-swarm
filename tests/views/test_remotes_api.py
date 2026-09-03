"""API tests for /v1/remotes/."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from swarm.core.remotes import HealthResult, OperateResult, RemoteSpec


@pytest.fixture
def api_client():
    return APIClient()


def _spec(rid: str = "hermes") -> RemoteSpec:
    return RemoteSpec(
        id=rid,
        title="t",
        host_label="box",
        base_url="http://10.0.0.36:8642",
        api_key="${HERMES_API_KEY}",
        notes="n",
        source="default",
    )


class TestRemotesList:
    @patch("swarm.views.remotes_api.remotes_core.list_team_members")
    @patch("swarm.views.remotes_api.remotes_core.load_added_remotes")
    def test_list_added(self, mock_load, mock_members, api_client):
        mock_load.return_value = {"hermes": _spec()}
        mock_members.return_value = [{"id": "hermes", "talk": "consult_hermes"}]
        resp = api_client.get("/v1/remotes/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "list"
        assert data["data"][0]["id"] == "hermes"
        assert data["data"][0]["api_key_set"] is False
        assert data["kinds"][0]["id"] == "hermes"
        assert any(k["id"] == "hermes" and k["complete"] is True for k in data["kinds"])
        assert "team_members" in data
        assert data["vocabulary"]["not_teams_page"]
        assert any(m["talk"] == "consult_hermes" for m in data["team_members"])

    @patch("swarm.views.remotes_api.remotes_core.list_team_members", return_value=[])
    @patch("swarm.views.remotes_api.remotes_core.load_added_remotes", return_value={})
    def test_list_empty_is_not_a_default_card(self, _added, _members, api_client):
        resp = api_client.get("/v1/remotes/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []
        assert any(k["id"] == "hermes" for k in data["kinds"])

    @patch("swarm.views.remotes_api.remotes_core.add_remote")
    def test_post_adds_hermes(self, mock_add, api_client):
        mock_add.return_value = (_spec(), "/tmp/swarm_config.json")
        resp = api_client.post(
            "/v1/remotes/",
            {
                "kind": "hermes",
                "base_url": "http://127.0.0.1:9",
                "api_key_env": "HERMES_API_KEY",
            },
            format="json",
        )
        assert resp.status_code == 200
        mock_add.assert_called_once()
        kwargs = mock_add.call_args.kwargs
        assert kwargs["base_url"] == "http://127.0.0.1:9"
        assert kwargs["api_key_env"] == "HERMES_API_KEY"
        assert "sk-" not in json.dumps(resp.json())

    def test_post_requires_kind(self, api_client):
        resp = api_client.post("/v1/remotes/", {"base_url": "http://127.0.0.1:9"}, format="json")
        assert resp.status_code == 400


class TestRemoteDetail:
    @patch("swarm.views.remotes_api.remotes_core.load_remote")
    @patch("swarm.views.remotes_api.remotes_core.is_remote_added", return_value=True)
    def test_get(self, _added, mock_load, api_client):
        mock_load.return_value = _spec()
        resp = api_client.get("/v1/remotes/hermes/")
        assert resp.status_code == 200
        assert resp.json()["base_url"] == "http://10.0.0.36:8642"

    @patch("swarm.views.remotes_api.remotes_core.is_remote_added", return_value=False)
    def test_missing_is_404_not_default(self, _added, api_client):
        resp = api_client.get("/v1/remotes/hermes/")
        assert resp.status_code == 404
        assert "not added" in resp.json()["error"]

    def test_unknown(self, api_client):
        resp = api_client.get("/v1/remotes/nope/")
        assert resp.status_code == 404

    @patch("swarm.views.remotes_api.remotes_core.persist_remote")
    def test_patch_persists(self, mock_persist, api_client):
        mock_persist.return_value = (_spec(), "/tmp/swarm_config.json")
        resp = api_client.patch(
            "/v1/remotes/hermes/",
            {"base_url": "http://10.0.0.36:8642", "api_key": "${HERMES_API_KEY}"},
            format="json",
        )
        assert resp.status_code == 200
        mock_persist.assert_called_once()
        assert resp.json()["persisted_to"] == "/tmp/swarm_config.json"

    def test_patch_empty(self, api_client):
        resp = api_client.patch("/v1/remotes/hermes/", {}, format="json")
        assert resp.status_code == 400


class TestRemoteHealth:
    @patch("swarm.views.remotes_api.remotes_core.check_health")
    @patch("swarm.views.remotes_api.remotes_core.is_remote_added", return_value=True)
    def test_down_is_200_report(self, _added, mock_health, api_client):
        mock_health.return_value = HealthResult(
            remote="hermes", ok=False, state="DOWN", detail="tcp refused"
        )
        resp = api_client.post("/v1/remotes/hermes/health/")
        assert resp.status_code == 200
        assert resp.json()["state"] == "DOWN"
        assert resp.json()["ok"] is False

    @patch("swarm.views.remotes_api.remotes_core.is_remote_added", return_value=False)
    def test_not_added_is_404(self, _added, api_client):
        resp = api_client.post("/v1/remotes/hermes/health/")
        assert resp.status_code == 404

    def test_unknown_remote(self, api_client):
        resp = api_client.post("/v1/remotes/nope/health/")
        assert resp.status_code == 404


class TestRemoteOperate:
    @patch("swarm.views.remotes_api.remotes_core.operate")
    @patch("swarm.views.remotes_api.remotes_core.is_remote_added", return_value=True)
    def test_list(self, _added, mock_op, api_client):
        mock_op.return_value = OperateResult(
            remote="hermes", op="list", ok=True, detail="listed", data={"models": []}
        )
        resp = api_client.post("/v1/remotes/hermes/operate/", {"op": "list"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_op.assert_called_once()

    @patch("swarm.views.remotes_api.remotes_core.is_remote_added", return_value=False)
    def test_not_added_is_404(self, _added, api_client):
        resp = api_client.post("/v1/remotes/hermes/operate/", {"op": "list"}, format="json")
        assert resp.status_code == 404


class TestAgentTeam:
    @patch("swarm.views.remotes_api.remotes_core.agent_team_public")
    def test_get(self, mock_pub, api_client):
        mock_pub.return_value = {
            "object": "agent_team",
            "members": ["hermes", "omb", "rakazo"],
            "team_members": [
                {"id": "hermes", "placed": True, "talk": "consult_hermes"},
            ],
            "not": "/v1/teams/ LLM-profile aliases (Profiles)",
        }
        resp = api_client.get("/v1/agent-team/")
        assert resp.status_code == 200
        assert resp.json()["object"] == "agent_team"
        assert "Profiles" in resp.json()["not"]

    @patch("swarm.views.remotes_api.remotes_core.agent_team_public")
    @patch("swarm.views.remotes_api.remotes_core.persist_agent_team")
    def test_patch_members(self, mock_persist, mock_pub, api_client):
        mock_persist.return_value = (["hermes"], "/tmp/swarm_config.json")
        mock_pub.return_value = {
            "object": "agent_team",
            "members": ["hermes"],
            "team_members": [
                {"id": "hermes", "placed": True},
                {"id": "omb", "placed": False},
                {"id": "rakazo", "placed": False},
            ],
        }
        resp = api_client.patch(
            "/v1/agent-team/",
            {"members": ["hermes"]},
            format="json",
        )
        assert resp.status_code == 200
        mock_persist.assert_called_once()
        assert resp.json()["persisted_to"] == "/tmp/swarm_config.json"
        assert resp.json()["members"] == ["hermes"]

    @patch("swarm.views.remotes_api.remotes_core.agent_team_public")
    @patch("swarm.views.remotes_api.remotes_core.unplace_team_member")
    def test_patch_unplace(self, mock_unplace, mock_pub, api_client):
        mock_unplace.return_value = (["hermes", "omb"], "/tmp/swarm_config.json")
        mock_pub.return_value = {"object": "agent_team", "members": ["hermes", "omb"]}
        resp = api_client.patch("/v1/agent-team/", {"unplace": "rakazo"}, format="json")
        assert resp.status_code == 200
        mock_unplace.assert_called_once()

    def test_patch_empty(self, api_client):
        resp = api_client.patch("/v1/agent-team/", {}, format="json")
        assert resp.status_code == 400
