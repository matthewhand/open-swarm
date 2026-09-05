"""API tests for /v1/cli-sessions/ (REQ-104)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from swarm.core import agent_settings as store
from swarm.core import chat_store
from swarm.core.cli_sessions import get_cli_session


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    monkeypatch.setenv("SWARM_AGY_CONVERSATIONS_DIR", str(tmp_path / "agy-conversations"))
    store.reset_agent_settings_cache()
    yield
    store.reset_agent_settings_cache()


def test_list_non_listable_is_honest(api_client):
    response = api_client.get("/v1/cli-sessions/?agent=cli_agent&cli=claude")
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "cli_session_list"
    assert body["can_list"] is False
    assert body["list_capability"] == "paste-only"
    assert body["sessions"] == []
    assert body["empty_reason"] == "This CLI can't list sessions"


def test_list_grok_without_binary_does_not_invent_rows(api_client, monkeypatch):
    from swarm.core import cli_catalog

    monkeypatch.setattr(cli_catalog, "which_cli", lambda exe: None)
    response = api_client.get("/v1/cli-sessions/?agent=cli_agent&cli=grok")
    assert response.status_code == 200
    body = response.json()
    assert body["can_list"] is True
    assert body["list_capability"] == "works"
    assert body["sessions"] == []
    assert body["activity_sot"] == "provider"
    assert "not installed" in (body.get("warning") or "").lower()


def test_select_paste_id_mints_conversation_and_stores_id(api_client, tmp_path):
    chat_store.save(
        "u0",
        "cli_agent",
        [{"role": "user", "content": "prior"}, {"role": "assistant", "content": "old"}],
        conversation_id="agt-guest-cli_agent",
        base_dir=tmp_path,
    )
    response = api_client.post(
        "/v1/cli-sessions/select/",
        {
            "agent": "cli_agent",
            "cli": "echo",
            "session_id": "sid-pasted",
            "from_conversation_id": "agt-guest-cli_agent",
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cli_session_id"] == "sid-pasted"
    assert body["conversation_id"] != "agt-guest-cli_agent"
    assert body["collapsed_prior"] is True
    assert get_cli_session("u0", "cli_agent", "echo") == "sid-pasted"
    assert any(m.get("kind") == "prior_history" for m in body["messages"])
    assert not any(m.get("role") in ("status", "info") for m in body["turns"])
    assert any(e.get("kind") == "prior_history" for e in body["ui_events"])
    assert any(e.get("content") == body["status"] for e in body["ui_events"])


def test_select_start_new(api_client):
    response = api_client.post(
        "/v1/cli-sessions/select/",
        {"agent": "cli_agent", "cli": "echo", "start_new": True},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cli_session_id"] is None
    assert body["status"] == "Started a new echo session."


def test_select_rejects_secret(api_client):
    response = api_client.post(
        "/v1/cli-sessions/select/",
        {"agent": "cli_agent", "cli": "echo", "session_id": "sk-live-secret-key"},
        format="json",
    )
    assert response.status_code == 400


def test_select_requires_id_or_start_new(api_client):
    response = api_client.post(
        "/v1/cli-sessions/select/",
        {"agent": "cli_agent", "cli": "echo"},
        format="json",
    )
    assert response.status_code == 400


def test_select_bad_folder_is_400(api_client, tmp_path):
    response = api_client.post(
        "/v1/cli-sessions/select/",
        {
            "agent": "cli_agent",
            "cli": "echo",
            "start_new": True,
            "folder": str(tmp_path / "missing"),
        },
        format="json",
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["error"]


def test_list_bad_folder_is_400(api_client, tmp_path):
    response = api_client.get(
        "/v1/cli-sessions/",
        {"agent": "cli_agent", "cli": "echo", "folder": str(tmp_path / "missing")},
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["error"]


def test_select_good_folder_starts(api_client, tmp_path):
    folder = tmp_path / "project"
    folder.mkdir()
    response = api_client.post(
        "/v1/cli-sessions/select/",
        {
            "agent": "cli_agent",
            "cli": "echo",
            "start_new": True,
            "folder": str(folder),
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Started a new echo session."
