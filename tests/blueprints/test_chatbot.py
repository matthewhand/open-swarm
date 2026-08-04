"""Tests for the chatbot blueprint (minimal single-agent REST template).

Mirrors the async/_collect/final-content style of test_cli_agent.py and
test_cli_fusion.py. The SWARM_TEST_MODE path is exercised directly so these
tests need no live LLM, API key, or network.
"""

from __future__ import annotations

import pytest

from swarm.blueprints.chatbot.blueprint_chatbot import ChatbotBlueprint


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
    # Deterministic, network-free path for every test in this module.
    monkeypatch.setenv("SWARM_TEST_MODE", "1")


# --------------------------------------------------------------------------- #
# Metadata / discovery
# --------------------------------------------------------------------------- #

def test_metadata_name_is_chatbot():
    assert ChatbotBlueprint.metadata["name"] == "chatbot"


def test_subclasses_blueprint_base():
    from swarm.core.blueprint_base import BlueprintBase

    assert issubclass(ChatbotBlueprint, BlueprintBase)


# --------------------------------------------------------------------------- #
# run() behaviour
# --------------------------------------------------------------------------- #

async def test_echoes_user_message():
    bp = ChatbotBlueprint(blueprint_id="chatbot")
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "You said: ping"


async def test_last_chunk_marked_final():
    bp = ChatbotBlueprint(blueprint_id="chatbot")
    chunks = await _collect(bp.run([{"role": "user", "content": "hi"}]))
    assert chunks[-1].get("final") is True


async def test_answer_is_nonempty_string():
    bp = ChatbotBlueprint(blueprint_id="chatbot")
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    final = _final_content(chunks)
    assert isinstance(final, str) and final.strip()


async def test_empty_messages_gives_greeting():
    bp = ChatbotBlueprint(blueprint_id="chatbot")
    chunks = await _collect(bp.run([]))
    final = _final_content(chunks)
    assert final == "Hello! How can I help you?"


async def test_blank_content_gives_greeting():
    bp = ChatbotBlueprint(blueprint_id="chatbot")
    chunks = await _collect(bp.run([{"role": "user", "content": "   "}]))
    assert _final_content(chunks) == "Hello! How can I help you?"


async def test_uses_latest_turn_in_multiturn():
    bp = ChatbotBlueprint(blueprint_id="chatbot")
    chunks = await _collect(
        bp.run(
            [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "ok"},
                {"role": "user", "content": "second"},
            ]
        )
    )
    assert _final_content(chunks) == "You said: second"


async def test_does_not_leak_spinner_text():
    # Guards the regression the API smoke matrix protects against.
    bp = ChatbotBlueprint(blueprint_id="chatbot")
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert not _final_content(chunks).startswith("Generating")
