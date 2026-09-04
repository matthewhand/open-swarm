"""API tests for /v1/agents/<id>/settings/ (REQ-65)."""

import pytest
from rest_framework.test import APIClient

from swarm.core import agent_settings as store
from swarm.core import session_policy as policy


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    store.reset_agent_settings_cache()
    policy.clear_active_sessions()
    yield
    store.reset_agent_settings_cache()
    policy.clear_active_sessions()


def test_get_defaults_off(api_client):
    response = api_client.get("/v1/agents/worker/settings/")
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "agent_settings"
    assert body["agent_id"] == "worker"
    assert body["new_chat_per_task"] is False


def test_patch_toggle_on(api_client):
    response = api_client.patch(
        "/v1/agents/worker/settings/",
        {"new_chat_per_task": True},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["new_chat_per_task"] is True
    again = api_client.get("/v1/agents/worker/settings/")
    assert again.json()["new_chat_per_task"] is True


def test_allocate_session_reuses_when_off(api_client):
    first = api_client.post("/v1/agents/worker/sessions/", {}, format="json")
    second = api_client.post("/v1/agents/worker/sessions/", {}, format="json")
    assert first.status_code == 200
    assert first.json()["new_chat_per_task"] is False
    assert first.json()["conversation_id"] == second.json()["conversation_id"]


def test_allocate_session_mints_when_on(api_client):
    api_client.patch(
        "/v1/agents/worker/settings/",
        {"new_chat_per_task": True},
        format="json",
    )
    first = api_client.post(
        "/v1/agents/worker/sessions/",
        {"task_id": "alpha"},
        format="json",
    )
    second = api_client.post(
        "/v1/agents/worker/sessions/",
        {"task_id": "beta"},
        format="json",
    )
    assert first.json()["empty"] is True
    assert first.json()["conversation_id"] != second.json()["conversation_id"]
