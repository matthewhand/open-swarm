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


def test_prod_path_passes_suggestions_agent(authenticated_client, monkeypatch):
    """Outside SWARM_TEST_MODE the API must pass a suggestions-role agent."""
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    store.update_settings("cli_agent", {"use_suggestions": True})

    class Stub:
        role = "suggestions"
        name = "suggester"

        def suggest(self, _prompt):
            return ["From specialist", "Second chip"]

    seen: dict = {}

    def wrap(*, mode, messages=None, agents=None, suggest_fn=None, consumer_id=None):
        seen["mode"] = mode
        seen["messages"] = messages
        seen["agents"] = agents
        seen["consumer_id"] = consumer_id
        from swarm.core.suggestions import run_suggestions as real

        return real(
            mode=mode,
            messages=messages,
            agents=agents,
            suggest_fn=suggest_fn,
            consumer_id=consumer_id,
        )

    monkeypatch.setattr("swarm.views.suggestions_api.run_suggestions", wrap)
    monkeypatch.setattr(
        "swarm.views.suggestions_api.resolve_suggestions_agents",
        lambda *_args, **_kwargs: [Stub()],
    )

    response = authenticated_client.get("/v1/agents/cli_agent/suggestions/?mode=kickstart")
    assert response.status_code == 200
    assert response.json()["suggestions"] == ["From specialist", "Second chip"]
    from swarm.core.agent_roles import ROLE_SUGGESTIONS, find_role_agent

    assert seen.get("agents") is not None
    assert find_role_agent(seen["agents"], ROLE_SUGGESTIONS) is not None


def test_prod_continue_passes_turn_messages(authenticated_client, monkeypatch, test_user):
    """Continue mode must load the consumer transcript, not omit messages."""
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    store.update_settings("api_agent", {"use_suggestions": True})

    from swarm.core.chat_store import save, user_key_for

    turns = [
        {"role": "user", "content": "Hello there"},
        {"role": "assistant", "content": "Hi back"},
    ]
    save(user_key_for(test_user), "api_agent", turns, conversation_id="conv-1")

    class Stub:
        role = "suggestions"
        name = "suggester"

        def suggest(self, prompt):
            assert "Hello there" in prompt
            return ["Go deeper on: Hello there", "What are the main risks?"]

    seen: dict = {}

    def wrap(*, mode, messages=None, agents=None, suggest_fn=None, consumer_id=None):
        seen["mode"] = mode
        seen["messages"] = messages
        seen["agents"] = agents
        seen["consumer_id"] = consumer_id
        from swarm.core.suggestions import run_suggestions as real

        return real(
            mode=mode,
            messages=messages,
            agents=agents,
            suggest_fn=suggest_fn,
            consumer_id=consumer_id,
        )

    monkeypatch.setattr("swarm.views.suggestions_api.run_suggestions", wrap)
    monkeypatch.setattr(
        "swarm.views.suggestions_api.resolve_suggestions_agents",
        lambda *_args, **_kwargs: [Stub()],
    )

    response = authenticated_client.get(
        "/v1/agents/api_agent/suggestions/?mode=continue&conversation_id=conv-1"
    )
    assert response.status_code == 200
    assert seen.get("mode") == "continue"
    assert seen.get("messages")
    assert seen["messages"][0]["content"] == "Hello there"
    from swarm.core.agent_roles import ROLE_SUGGESTIONS, find_role_agent

    assert find_role_agent(seen["agents"], ROLE_SUGGESTIONS) is not None
    assert "Go deeper on: Hello there" in response.json()["suggestions"]


def test_support_kickstart_returns_journey_chips(api_client):
    api_client.patch(
        "/v1/agents/support/settings/",
        {"use_suggestions": True},
        format="json",
    )
    response = api_client.get("/v1/agents/support/suggestions/?mode=kickstart")
    assert response.status_code == 200
    chips = " ".join(response.json()["suggestions"]).lower()
    assert "create a team" in chips
    assert "add a remote" in chips
    assert "wire a cli" in chips


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
