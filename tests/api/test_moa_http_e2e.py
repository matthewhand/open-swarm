"""Full Django APIClient e2e for model=moa (HTTP leftover fix)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from swarm.blueprints.moa.blueprint_moa import MoABlueprint


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_http_e2e_moa_chat_completions_fingerprint(api_client):
    """POST /v1/chat/completions with real MoABlueprint + fake panel → fingerprint."""

    async def fake_get_instance(model_name, params=None):
        assert model_name in ("moa", "mixture_of_agents", "cli_fusion")
        bp = MoABlueprint(blueprint_id=model_name)
        bp._config = {}
        # set_params is what chat_views → get_blueprint_instance does
        bp.set_params(
            params
            or {
                "participants": ["claude", "codex"],
                "fake_responses": {
                    "claude": '{"claim":"token bucket","confidence":0.9}',
                    "codex": '{"claim":"token bucket with metrics","confidence":0.85}',
                },
            }
        )
        return bp

    with patch(
        "swarm.views.chat_views.get_blueprint_instance",
        new=AsyncMock(side_effect=fake_get_instance),
    ), patch(
        "swarm.views.chat_views.validate_model_access",
        return_value=True,
    ):
        response = api_client.post(
            "/v1/chat/completions",
            {
                "model": "moa",
                "messages": [{"role": "user", "content": "How should we rate-limit?"}],
                "stream": False,
                "params": {
                    "participants": ["claude", "codex"],
                    "fake_responses": {
                        "claude": '{"claim":"token bucket","confidence":0.9}',
                        "codex": '{"claim":"token bucket with metrics","confidence":0.85}',
                    },
                },
            },
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK, response.content
    data = response.json()
    assert data["model"] == "moa"
    content = data["choices"][0]["message"]["content"]
    assert "token bucket" in content.lower()
    # system_fingerprint names the panelists that answered
    fp = data.get("system_fingerprint") or ""
    assert fp.startswith("moa:")
    assert "claude" in fp and "codex" in fp


@pytest.mark.django_db
def test_http_e2e_legacy_alias_cli_fusion(api_client):
    """Legacy model id cli_fusion resolves to MoA (read-only) via get_blueprint_instance."""

    async def fake_get_instance(model_name, params=None):
        assert model_name == "cli_fusion"
        bp = MoABlueprint(blueprint_id="cli_fusion")
        bp._config = {}
        bp.set_params(
            {
                "participants": ["a"],
                "fake_responses": {"a": '{"claim":"ok","confidence":1}'},
            }
        )
        return bp

    with patch(
        "swarm.views.chat_views.get_blueprint_instance",
        new=AsyncMock(side_effect=fake_get_instance),
    ), patch(
        "swarm.views.chat_views.validate_model_access",
        return_value=True,
    ):
        response = api_client.post(
            "/v1/chat/completions",
            {
                "model": "cli_fusion",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "params": {
                    "participants": ["a"],
                    "fake_responses": {"a": '{"claim":"ok","confidence":1}'},
                },
            },
            format="json",
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["choices"][0]["message"]["content"]
    assert "cli_fusion" in (response.json().get("system_fingerprint") or "cli_fusion")
