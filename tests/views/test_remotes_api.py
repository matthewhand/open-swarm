"""API tests for /v1/remotes/."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from swarm.core.remotes import HealthResult, OperateResult, RemoteError, RemoteSpec


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
    @patch("swarm.views.remotes_api.remotes_core.list_configured_remotes")
    @patch("swarm.views.remotes_api.remotes_core.load_all_remotes")
    def test_list(self, mock_load, mock_configured, mock_members, api_client):
        mock_load.return_value = {"hermes": _spec()}
        mock_configured.return_value = []
        mock_members.return_value = [{"id": "hermes", "talk": "consult_hermes", "placed": False}]
        resp = api_client.get("/v1/remotes/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "list"
        assert data["data"][0]["id"] == "hermes"
        assert data["data"][0]["api_key_set"] is False
        assert data["configured"] == []
        assert any(k["id"] == "omb" and k["label"] == "OpenMousBot" for k in data["kinds"])
        assert all(k["label"] != "OMB" for k in data["kinds"])
        assert "team_members" in data
        assert data["vocabulary"]["not_teams_page"]
        assert any(m["talk"] == "consult_hermes" for m in data["team_members"])

    @patch("swarm.views.remotes_api.remotes_core.persist_remote")
    def test_create(self, mock_persist, api_client):
        spec = _spec("omb")
        spec.title = "OpenMousBot"
        mock_persist.return_value = (spec, "/tmp/swarm_config.json")
        resp = api_client.post(
            "/v1/remotes/",
            {"kind": "omb", "base_url": "http://127.0.0.1:8802"},
            format="json",
        )
        assert resp.status_code == 201
        mock_persist.assert_called_once()
        body = resp.json()
        assert body["id"] == "omb"
        assert body["label"] == "OpenMousBot"
        assert body["persisted_to"] == "/tmp/swarm_config.json"

    @patch("swarm.views.remotes_api.remotes_core.persist_remote")
    def test_create_rakazo_env_names(self, mock_persist, api_client):
        spec = _spec("rakazo")
        spec.title = "Rakazo"
        spec.api_key_env = "RAKAZO_API_KEY"
        spec.session_cookie_env = "RAKAZO_SESSION_COOKIE"
        spec.ui_url = "http://127.0.0.1:5173"
        mock_persist.return_value = (spec, "/tmp/swarm_config.json")
        resp = api_client.post(
            "/v1/remotes/",
            {
                "kind": "rakazo",
                "base_url": "http://127.0.0.1:4173",
                "ui_url": "http://127.0.0.1:5173",
                "api_key_env": "RAKAZO_API_KEY",
                "session_cookie_env": "RAKAZO_SESSION_COOKIE",
            },
            format="json",
        )
        assert resp.status_code == 201
        mock_persist.assert_called_once()
        kwargs = mock_persist.call_args.kwargs
        assert kwargs["api_key_env"] == "RAKAZO_API_KEY"
        assert kwargs["session_cookie_env"] == "RAKAZO_SESSION_COOKIE"
        assert kwargs["ui_url"] == "http://127.0.0.1:5173"
        body = resp.json()
        assert body["api_key_env"] == "RAKAZO_API_KEY"
        assert body["session_cookie_env"] == "RAKAZO_SESSION_COOKIE"
        assert "api_key" not in body


class TestRemoteDetail:
    @patch("swarm.views.remotes_api.remotes_core.load_remote")
    def test_get(self, mock_load, api_client):
        mock_load.return_value = _spec()
        resp = api_client.get("/v1/remotes/hermes/")
        assert resp.status_code == 200
        assert resp.json()["base_url"] == "http://10.0.0.36:8642"

    @patch("swarm.views.remotes_api.remotes_core.load_remote")
    def test_unknown(self, mock_load, api_client):
        mock_load.side_effect = RemoteError("Unknown remote 'nope'")
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

    @patch("swarm.views.remotes_api.remotes_core.delete_remote")
    def test_delete(self, mock_delete, api_client):
        mock_delete.return_value = ("omb", "/tmp/swarm_config.json")
        resp = api_client.delete("/v1/remotes/omb/")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
        mock_delete.assert_called_once()

    @patch("swarm.views.remotes_api.remotes_core.delete_remote")
    def test_delete_missing(self, mock_delete, api_client):
        mock_delete.side_effect = RemoteError("Remote 'omb' is not configured")
        resp = api_client.delete("/v1/remotes/omb/")
        assert resp.status_code == 404

    @patch("swarm.views.remotes_api.remotes_core.persist_remote")
    def test_patch_swarm_refuses_self(self, mock_persist, api_client):
        mock_persist.side_effect = RemoteError(
            "Refusing to nest this server as its own remote "
            "(base_url http://127.0.0.1:8000 matches this process listen URL)."
        )
        resp = api_client.patch(
            "/v1/remotes/swarm/",
            {"base_url": "http://127.0.0.1:8000", "api_key": "${CHANGE_ME}"},
            format="json",
        )
        assert resp.status_code == 400
        assert "own remote" in resp.json()["error"]


class TestRemoteHealth:
    @patch("swarm.views.remotes_api.remotes_core.check_health")
    def test_down_is_200_report(self, mock_health, api_client):
        mock_health.return_value = HealthResult(
            remote="hermes", ok=False, state="DOWN", detail="tcp refused"
        )
        resp = api_client.post("/v1/remotes/hermes/health/")
        assert resp.status_code == 200
        assert resp.json()["state"] == "DOWN"
        assert resp.json()["ok"] is False

    def test_unknown_remote(self, api_client):
        resp = api_client.post("/v1/remotes/nope/health/")
        assert resp.status_code == 404


class TestRemoteOperate:
    @patch("swarm.views.remotes_api.remotes_core.operate")
    def test_list(self, mock_op, api_client):
        mock_op.return_value = OperateResult(
            remote="omb", op="list", ok=True, detail="listed", data={"bots": []}
        )
        resp = api_client.post("/v1/remotes/omb/operate/", {"op": "list"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_op.assert_called_once()

    @patch("swarm.views.remotes_api.remotes_core.operate")
    def test_swarm_send(self, mock_op, api_client):
        mock_op.return_value = OperateResult(
            remote="swarm",
            op="send",
            ok=True,
            detail="sent nested swarm turn",
            data={"model": "echo"},
        )
        resp = api_client.post(
            "/v1/remotes/swarm/operate/",
            {"op": "send", "prompt": "ping", "target": "echo"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["remote"] == "swarm"


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
