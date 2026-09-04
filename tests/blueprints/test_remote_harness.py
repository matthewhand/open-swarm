"""Tests for the remote_harness blueprint grammar and as_tool wiring."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from swarm.blueprints.remote_harness.blueprint_remote_harness import RemoteHarnessBlueprint
from swarm.core.blueprint_discovery import discover_blueprints
from swarm.core.remotes import HealthResult, OperateResult


async def _collect(gen):
    return [c async for c in gen]


def _final(chunks):
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content"):
            return msgs[0]["content"]
    return None


@pytest.fixture
def bp():
    return RemoteHarnessBlueprint(config={"llm": {}})


async def _ask(bp, content, params=None):
    bp.set_params(params or {})
    return _final(await _collect(bp.run([{"role": "user", "content": content}])))


def test_remote_harness_is_discoverable():
    found = discover_blueprints("src/swarm/blueprints")
    assert "remote_harness" in found


@pytest.mark.asyncio
async def test_health_grammar(bp):
    with patch(
        "swarm.blueprints.remote_harness.blueprint_remote_harness.remotes_core.check_health",
        return_value=HealthResult(remote="hermes", ok=False, state="DOWN", detail="tcp timeout"),
    ) as probe:
        out = await _ask(bp, "health hermes")
    assert "DOWN" in out
    assert "hermes" in out
    probe.assert_called()


@pytest.mark.asyncio
async def test_list_config_without_probing(bp):
    out = await _ask(bp, "list")
    assert "hermes" in out
    assert "omb" in out
    assert "rakazo" in out
    assert "swarm" in out
    assert "10.0.0.36:8642" in out
    assert "127.0.0.1:9" in out


@pytest.mark.asyncio
async def test_send_params(bp):
    with patch(
        "swarm.blueprints.remote_harness.blueprint_remote_harness.remotes_core.operate",
        return_value=OperateResult(remote="hermes", op="send", ok=True, detail="started"),
    ) as op:
        out = await _ask(bp, "", params={"op": "send", "name": "hermes", "prompt": "hi"})
    assert "OK" in out
    op.assert_called_once()


@pytest.mark.asyncio
async def test_as_tool_specialists_wired(bp):
    agents = bp._build_agents()
    assert agents, "expected coordinator + specialist agents (bare Agent fallback if no LLM)"
    coord = agents["coordinator"]
    names = []
    for tool in getattr(coord, "tools", []) or []:
        names.append(getattr(tool, "name", None) or getattr(tool, "__name__", ""))
    joined = " ".join(str(n) for n in names)
    assert "consult_hermes" in joined
    assert "consult_omb" in joined
    assert "consult_rakazo" in joined


@pytest.mark.asyncio
async def test_as_tool_only_placed_members():
    bp = RemoteHarnessBlueprint(
        config={"llm": {}, "agent_team": {"members": ["hermes"]}}
    )
    agents = bp._build_agents()
    assert agents, "expected coordinator + placed specialist"
    assert "hermes" in agents
    assert "omb" not in agents
    assert "rakazo" not in agents
    assert "swarm" not in agents
    names = []
    for tool in getattr(agents["coordinator"], "tools", []) or []:
        names.append(getattr(tool, "name", None) or getattr(tool, "__name__", ""))
    joined = " ".join(str(n) for n in names)
    assert "consult_hermes" in joined
    assert "consult_omb" not in joined
    assert "consult_rakazo" not in joined
    assert "consult_swarm" not in joined


@pytest.mark.asyncio
async def test_as_tool_swarm_when_placed():
    bp = RemoteHarnessBlueprint(
        config={"llm": {}, "agent_team": {"members": ["swarm"]}}
    )
    agents = bp._build_agents()
    assert agents, "expected coordinator + swarm specialist"
    assert "swarm" in agents
    assert "hermes" not in agents
    names = []
    for tool in getattr(agents["coordinator"], "tools", []) or []:
        names.append(getattr(tool, "name", None) or getattr(tool, "__name__", ""))
    joined = " ".join(str(n) for n in names)
    assert "consult_swarm" in joined
