"""REQ-50: Support always attaches the session-ownership skill."""

from __future__ import annotations

from swarm.blueprints.common import cli_fusion_support as fusion
from swarm.blueprints.common.support_blueprint import (
    CLICK_BUBBLE_TO_EDIT,
    SUPPORT_SKILL_FIXTURE,
    SUPPORT_SKILL_NAME,
    SupportBlueprint,
    resolve_session_kind,
    support_turn_context,
    support_turn_reply,
)
from swarm.core import skills


def _bp(**params) -> SupportBlueprint:
    bp = SupportBlueprint(blueprint_id="support", config={})
    if params:
        bp.set_params(params)
    return bp


async def _collect(gen):
    chunks = []
    async for chunk in gen:
        chunks.append(chunk)
    return chunks


def _final_content(chunks):
    text = None
    for chunk in chunks:
        msgs = chunk.get("messages") if isinstance(chunk, dict) else None
        if msgs and msgs[0].get("content") is not None:
            text = msgs[0]["content"]
    return text


def test_skill_is_discoverable_and_carries_fixture():
    found = skills.discover_skills()
    assert SUPPORT_SKILL_NAME in found
    skill = found[SUPPORT_SKILL_NAME]
    assert SUPPORT_SKILL_FIXTURE in skill.instructions
    assert "use when" in skill.description.lower()


def test_apply_skill_to_prompt_attaches_support_skill():
    prompt, name = fusion.apply_skill_to_prompt("hello", {"skill": SUPPORT_SKILL_NAME})
    assert name == SUPPORT_SKILL_NAME
    assert SUPPORT_SKILL_FIXTURE in prompt
    assert prompt.rstrip().endswith("hello")


def test_support_context_includes_skill_fixture():
    ctx = support_turn_context("api", "how do I edit that?")
    assert SUPPORT_SKILL_FIXTURE in ctx
    assert SUPPORT_SKILL_NAME in ctx


def test_support_blueprint_system_prompt_includes_fixture():
    prompt = _bp().system_prompt([{"role": "user", "content": "hi"}])
    assert SUPPORT_SKILL_FIXTURE in prompt
    assert "SKILL INSTRUCTIONS" in prompt


async def test_cli_mode_support_turn_does_not_claim_click_edit(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    bp = _bp(session_kind="cli", skill=SUPPORT_SKILL_NAME)
    chunks = await _collect(
        bp.run([{"role": "user", "content": "how do I edit that last bubble?"}])
    )
    text = _final_content(chunks)
    assert text
    assert CLICK_BUBBLE_TO_EDIT not in text.lower()
    assert "outside" in text.lower()


async def test_remote_mode_support_turn_does_not_claim_click_edit(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    bp = _bp(session_kind="remote")
    chunks = await _collect(bp.run([{"role": "user", "content": "can I edit this?"}]))
    assert CLICK_BUBBLE_TO_EDIT not in _final_content(chunks).lower()


def test_cli_reply_helper_never_says_click_edit():
    reply = support_turn_reply([{"role": "user", "content": "edit?"}], "cli")
    assert CLICK_BUBBLE_TO_EDIT not in reply.lower()


def test_resolve_session_kind_explicit_and_heuristic():
    assert resolve_session_kind({"session_kind": "cli"}) == "cli"
    assert resolve_session_kind({}, [{"role": "user", "content": "my grok session"}]) == "cli"
    assert resolve_session_kind({}, [{"role": "user", "content": "hello"}]) == "api"


def test_support_metadata_role():
    assert SupportBlueprint.metadata["name"] == "support"
    assert SupportBlueprint.metadata.get("role") == "support"
