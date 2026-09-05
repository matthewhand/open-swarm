"""REQ-85: GET /v1/agents/<id>/suggestions/."""

import pytest
from rest_framework.test import APIClient

from swarm.core import agent_settings as store


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    store.reset_agent_settings_cache()
    yield
    store.reset_agent_settings_cache()


def test_suggestions_off_returns_empty(api_client):
    response = api_client.get("/v1/agents/worker/suggestions/")
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "suggestions"
    assert body["suggestions"] == []


def test_suggestions_on_kickstart(api_client):
    api_client.patch(
        "/v1/agents/worker/settings/",
        {"use_suggestions": True},
        format="json",
    )
    response = api_client.get("/v1/agents/worker/suggestions/?mode=kickstart")
    assert response.status_code == 200
    chips = response.json()["suggestions"]
    assert 2 <= len(chips) <= 5
    assert all(isinstance(item, str) and item for item in chips)


def test_settings_roundtrip_use_suggestions(api_client):
    first = api_client.get("/v1/agents/worker/settings/")
    assert first.json()["use_suggestions"] is False
    patched = api_client.patch(
        "/v1/agents/worker/settings/",
        {"use_suggestions": True},
        format="json",
    )
    assert patched.json()["use_suggestions"] is True
    again = api_client.get("/v1/agents/worker/settings/")
    assert again.json()["use_suggestions"] is True
