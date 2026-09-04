"""Agent Creator codegen must stream via AsyncOpenAI — not chat_completion_stream."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


def _llm_config() -> dict:
    return {
        "llm": {
            "default": {
                "provider": "openai",
                "model": "test-model",
                "api_key": "sk-test",
                "base_url": "http://127.0.0.1:9/v1",
            }
        },
        "llm_profile": "default",
    }


def _load_generated(code: str):
    ns: dict = {"__name__": "generated_agent_creator_bp"}
    exec(compile(code, "<agent_creator_generate>", "exec"), ns)
    classes = [
        v
        for k, v in ns.items()
        if isinstance(v, type) and k.endswith("Blueprint") and k != "BlueprintBase"
    ]
    assert len(classes) == 1, f"expected one Blueprint class, got {classes!r}"
    return ns, classes[0]


@pytest.mark.django_db
def test_agent_persona_generator_streams_via_async_openai(monkeypatch):
    """Django /agent-creator/ must not emit nonexistent chat_completion_stream."""
    monkeypatch.delenv("LITELLM_MODEL", raising=False)
    monkeypatch.delenv("DEFAULT_LLM", raising=False)
    from swarm.views.agent_creator_views import AgentPersonaGenerator

    code = AgentPersonaGenerator().generate_agent_code(
        {
            "name": "Creator Stream Agent",
            "description": "agent-creator codegen closer",
            "personality": "precise",
            "expertise": ["testing"],
            "communication_style": "terse",
            "instructions": "Reply briefly.",
            "tags": ["golden", "creator"],
        }
    )
    assert "chat_completion_stream" not in code
    assert "_get_model_instance" not in code
    assert "AsyncOpenAI" in code
    assert "chat.completions.create" in code
    assert "stream=True" in code
    assert "falling back to echo" in code

    ns, cls = _load_generated(code)

    async def stream():
        for part in ("Hi", " creator"):
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = part
            yield chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=stream())
    ns["AsyncOpenAI"] = MagicMock(return_value=mock_client)

    bp = cls(blueprint_id="creator_stream_agent", config=_llm_config())

    async def collect():
        out = []
        async for ch in bp.run([{"role": "user", "content": "ping"}]):
            out.append(ch)
        return out

    chunks = asyncio.run(collect())
    text = "".join(c["messages"][0]["content"] for c in chunks)
    assert text == "Hi creator"
    assert "You said:" not in text
    create_kwargs = mock_client.chat.completions.create.await_args.kwargs
    assert create_kwargs["stream"] is True
    assert create_kwargs["model"] == "test-model"
    assert create_kwargs["messages"][0]["role"] == "system"
    assert "Creator Stream Agent" in create_kwargs["messages"][0]["content"]


@pytest.mark.django_db
def test_agent_persona_generator_echo_fallback_on_llm_failure():
    from swarm.views.agent_creator_views import AgentPersonaGenerator

    code = AgentPersonaGenerator().generate_agent_code(
        {
            "name": "Echo Fallback Creator",
            "description": "warned echo path",
            "tags": ["echo"],
        }
    )
    ns, cls = _load_generated(code)
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("llm down")
    )
    ns["AsyncOpenAI"] = MagicMock(return_value=mock_client)
    bp = cls(blueprint_id="echo_fallback_creator", config=_llm_config())

    async def collect():
        out = []
        async for ch in bp.run([{"role": "user", "content": "ping"}]):
            out.append(ch)
        return out

    chunks = asyncio.run(collect())
    assert len(chunks) == 1
    content = chunks[0]["messages"][0]["content"]
    assert "WARNING: LLM call failed" in content
    assert "falling back to echo" in content
    assert "You said: ping" in content
