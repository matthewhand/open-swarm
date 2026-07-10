"""API surface for MoA model id + fingerprint (leftover HTTP wire)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from swarm.blueprints.moa.blueprint_moa import MoABlueprint, LEGACY_ALIASES
from swarm.core.blueprint_discovery import discover_blueprints
from swarm.views.chat_views import ChatCompletionsView, backend_fingerprint


def test_discover_moa_and_aliases():
    root = Path(__file__).resolve().parents[2] / "src" / "swarm" / "blueprints"
    found = discover_blueprints(str(root))
    assert "moa" in found
    # Aliases registered for chat model ids
    for alias in ("mixture_of_agents", "cli_fusion", "cli_ensemble"):
        assert alias in found, f"missing alias {alias}"
        assert found[alias]["class_type"] is found["moa"]["class_type"]


@pytest.mark.asyncio
async def test_moa_blueprint_yields_messages_and_meta():
    bp = MoABlueprint(blueprint_id="moa")
    bp._config = {}
    bp.set_params(
        {
            "participants": ["a", "b"],
            "fake_responses": {
                "a": '{"claim":"yes","confidence":0.9}',
                "b": '{"claim":"yes with tests","confidence":0.8}',
            },
        }
    )
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Ship it?"}]):
        chunks.append(c)
    assert chunks
    final = chunks[-1]
    assert "messages" in final
    assert final["messages"][0]["role"] == "assistant"
    assert final["meta"]["moa"] is True
    assert "backends" in final["meta"]
    assert final["meta"]["backends"]


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_chat_completions_moa_fingerprint(monkeypatch):
    """Non-streaming path sets system_fingerprint from MoA meta."""
    factory = APIRequestFactory()
    view = ChatCompletionsView.as_view()

    class FakeBP:
        async def run(self, messages, stream=False):
            yield {
                "messages": [{"role": "assistant", "content": "token bucket"}],
                "final": True,
                "meta": {"backends": ["claude", "codex"], "moa": True},
            }

    async def fake_get_instance(model_name, params=None):
        assert model_name == "moa"
        return FakeBP()

    with patch(
        "swarm.views.chat_views.get_blueprint_instance",
        new=AsyncMock(side_effect=fake_get_instance),
    ), patch(
        "swarm.views.chat_views.validate_model_access",
        return_value=True,
    ):
        request = factory.post(
            "/v1/chat/completions",
            {
                "model": "moa",
                "messages": [{"role": "user", "content": "rate limit?"}],
                "stream": False,
                "params": {"participants": ["claude", "codex"]},
            },
            format="json",
        )
        # DRF APIView async: use view dispatch carefully
        from rest_framework.request import Request
        from rest_framework.parsers import JSONParser

        # Use the class method path directly for reliability
        api_view = ChatCompletionsView()
        api_view.format_kwarg = None
        req = Request(request)
        # serializer path is heavy; call helper with fake instance
        resp = await api_view._handle_non_streaming(
            FakeBP(),
            [{"role": "user", "content": "rate limit?"}],
            "test-req",
            "moa",
        )
    assert resp.status_code == 200
    data = resp.data
    assert data["choices"][0]["message"]["content"] == "token bucket"
    assert data["system_fingerprint"] == "moa:claude+codex"


def test_legacy_aliases_constant():
    assert "cli_fusion" in LEGACY_ALIASES
    assert "cli_ensemble" in LEGACY_ALIASES
