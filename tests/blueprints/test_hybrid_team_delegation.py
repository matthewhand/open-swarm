"""claude-orchestrated structured delegation in hybrid_team.

The orchestration brain (claude -p, when configured) returns a JSON plan +
role delegations; run() parses them and routes each to its role's model. These
tests cover the pure parsing + the deterministic test-mode routing, plus the
claude path with a mocked persona (no live CLI / network).
"""
from __future__ import annotations

from swarm.blueprints.hybrid_team.blueprint_hybrid_team import HybridTeamBlueprint

CONFIG = {"llm": {"default": {"provider": "openai", "model": "d"}}}


def _bp() -> HybridTeamBlueprint:
    return HybridTeamBlueprint(config=CONFIG)


# --- _parse_delegations ---------------------------------------------------- #

def test_parse_clean_json():
    raw = '{"plan":"do x","delegations":[{"role":"agent","task":"code it"},{"role":"auxiliary","task":"test it"}]}'
    plan, dels = _bp()._parse_delegations(raw)
    assert plan == "do x"
    assert dels == [{"role": "agent", "task": "code it"}, {"role": "auxiliary", "task": "test it"}]


def test_parse_json_embedded_in_prose():
    raw = 'Sure!\n{"plan":"p","delegations":[{"role":"orchestration","task":"plan more"}]}\nDone.'
    plan, dels = _bp()._parse_delegations(raw)
    assert plan == "p"
    assert dels == [{"role": "orchestration", "task": "plan more"}]


def test_parse_drops_unknown_role_and_empty_task():
    raw = ('{"plan":"p","delegations":['
           '{"role":"wizard","task":"magic"},'
           '{"role":"agent","task":""},'
           '{"role":"AUXILIARY","task":"normalize case"}]}')
    _, dels = _bp()._parse_delegations(raw)
    assert dels == [{"role": "auxiliary", "task": "normalize case"}]  # case-normalized, unknown/empty dropped


def test_parse_non_json_degrades_to_plain_plan():
    plan, dels = _bp()._parse_delegations("just a plan, no json", fallback="fb")
    assert plan == "just a plan, no json"
    assert dels == []


def test_parse_empty_uses_fallback():
    plan, dels = _bp()._parse_delegations("", fallback="fb")
    assert plan == "fb"
    assert dels == []


# --- deterministic test-mode routing --------------------------------------- #

async def test_run_delegation_is_deterministic_in_test_mode(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    out = await _bp()._run_delegation({"role": "agent", "task": "do the thing"})
    assert out == "[agent] do the thing"


async def test_orchestrate_stub_in_test_mode(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    plan, dels = await _bp()._orchestrate("hi", registry=None)
    assert plan == "[rest-plan] hi"
    assert dels == []


# --- claude path (mocked persona, no live CLI) ----------------------------- #

async def test_orchestrate_uses_claude_json(monkeypatch):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    bp = _bp()

    async def fake_claude(prompt):
        return '{"plan":"P","delegations":[{"role":"agent","task":"T"}]}'

    monkeypatch.setattr(bp, "_claude_persona", lambda registry: fake_claude)
    plan, dels = await bp._orchestrate("req", registry=object())
    assert plan == "P"
    assert dels == [{"role": "agent", "task": "T"}]


async def test_orchestrate_without_claude_falls_back_to_plan(monkeypatch):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    bp = _bp()
    monkeypatch.setattr(bp, "_claude_persona", lambda registry: None)

    async def fake_rest(prompt):
        return "plain plan"

    monkeypatch.setattr(bp, "_rest_reason", fake_rest)
    plan, dels = await bp._orchestrate("req", registry=object())
    assert plan == "plain plan"
    assert dels == []
