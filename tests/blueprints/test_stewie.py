"""Stewie blueprint: hermetic SWARM_TEST_MODE coverage."""

from __future__ import annotations

import pytest

from swarm.blueprints.stewie.blueprint_stewie import StewieBlueprint
from swarm.core.blueprint_base import BlueprintBase


async def _collect(gen):
    return [c async for c in gen]


def _final_content(chunks):
    text = None
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content") is not None:
            text = msgs[0]["content"]
    return text


@pytest.fixture(autouse=True)
def _test_mode(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")


def test_metadata_and_subclass():
    assert issubclass(StewieBlueprint, BlueprintBase)
    assert StewieBlueprint.metadata.get("title")
    assert "wordpress" in (StewieBlueprint.metadata.get("tags") or [])
    # dirname id remains the discoverable model id
    bp = StewieBlueprint(blueprint_id="stewie")
    assert bp.blueprint_id == "stewie"


@pytest.mark.asyncio
async def test_test_mode_echoes_instruction():
    bp = StewieBlueprint(blueprint_id="stewie")
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    text = _final_content(chunks)
    assert text is not None
    assert "[TEST-MODE]" in text
    assert "ping" in text
    assert "Stewie" in text or "deuce" in text.lower()


def test_unknown_llm_profile_warns_then_falls_back(monkeypatch):
    """Named miss must warn (not silent {}); default profile still used."""
    import logging
    from unittest.mock import MagicMock, patch

    config = {
        "llm": {
            "default": {
                "provider": "openai",
                "model": "gpt-mock",
                "api_key": "k",
            }
        },
        "llm_profile": "default",
    }
    bp = StewieBlueprint(blueprint_id="stewie", config=config)
    warned: list[str] = []
    original = logging.Logger.warning

    def _capture(self, msg, *args, **kwargs):
        warned.append(msg % args if args else str(msg))
        return original(self, msg, *args, **kwargs)

    monkeypatch.setattr(logging.Logger, "warning", _capture)
    with patch(
        "swarm.blueprints.stewie.blueprint_stewie.OpenAIChatCompletionsModel",
        return_value=MagicMock(name="model"),
    ), patch(
        "swarm.blueprints.stewie.blueprint_stewie.AsyncOpenAI",
        return_value=MagicMock(name="client"),
    ):
        model = bp._get_model_instance("not-a-real-profile")
    assert model is not None
    assert any("not-a-real-profile" in w and "falling back" in w.lower() for w in warned)


def test_profile_credentials_preferred_over_env(monkeypatch):
    """LLM profile base_url/api_key win over process env (Jules #293)."""
    from unittest.mock import MagicMock, patch

    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example")
    monkeypatch.setenv("LITELLM_API_KEY", "env-litellm-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "https://env-litellm.example")

    config = {
        "llm": {
            "default": {
                "provider": "openai",
                "model": "gpt-mock",
                "api_key": "profile-key",
                "base_url": "https://profile.example",
            }
        },
        "llm_profile": "default",
    }
    bp = StewieBlueprint(blueprint_id="stewie", config=config)
    with patch(
        "swarm.blueprints.stewie.blueprint_stewie.OpenAIChatCompletionsModel",
        return_value=MagicMock(name="model"),
    ), patch(
        "swarm.blueprints.stewie.blueprint_stewie.AsyncOpenAI",
        return_value=MagicMock(name="client"),
    ) as mock_client:
        assert bp._get_model_instance("default") is not None

    mock_client.assert_called_once()
    kwargs = mock_client.call_args.kwargs
    assert kwargs["api_key"] == "profile-key"
    assert kwargs["base_url"] == "https://profile.example"
