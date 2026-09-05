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
    store.reset_agent_settings_cache()
    yield
    store.reset_agent_settings_cache()


def test_list_non_listable_is_honest(api_client):
    response = api_client.get("/v1/cli-sessions/?agent=cli_agent&cli=grok")
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "cli_session_list"
    assert body["can_list"] is False
    assert body["sessions"] == []
    assert body["empty_reason"] == "This CLI can't list sessions"


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
