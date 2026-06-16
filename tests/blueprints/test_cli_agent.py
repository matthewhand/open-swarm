"""Tests for the single-CLI blueprint (cli_agent) and shared support helpers."""

from __future__ import annotations

import sys

import pytest

from swarm.blueprints.cli_agent.blueprint_cli_agent import CliAgentBlueprint
from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.cli_adapter import CliAdapterRegistry

PY = sys.executable


def _echo_config(prefix: str = "ECHO") -> dict:
    return {
        "cli_agents": {
            "echo": {
                "cmd": [PY, "-c", f"import sys; print('{prefix}: ' + sys.argv[1])", "{prompt}"],
                "parse": "text",
            },
            "echo2": {
                "cmd": [PY, "-c", "import sys; print('TWO: ' + sys.argv[1])", "{prompt}"],
            },
        },
        "cli_fusion": {"default_cli": "echo"},
    }


async def _collect(gen):
    chunks = []
    async for c in gen:
        chunks.append(c)
    return chunks


def _final_content(chunks):
    text = None
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content") is not None:
            text = msgs[0]["content"]
    return text


# --------------------------------------------------------------------------- #
# Support helpers
# --------------------------------------------------------------------------- #

def test_render_prompt_single():
    assert support.render_prompt([{"role": "user", "content": "hi"}]) == "hi"


def test_render_prompt_multiturn_transcript():
    out = support.render_prompt(
        [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hello"},
        ]
    )
    assert "SYSTEM: be terse" in out and "USER: hello" in out


def test_select_single_cli_priority():
    cfg = _echo_config()
    reg = CliAdapterRegistry.from_config(cfg)
    # per-request param wins
    assert support.select_single_cli(cfg, {"cli": "echo2"}, reg) == "echo2"
    # else config default
    assert support.select_single_cli(cfg, {}, reg) == "echo"


def test_select_single_cli_none_when_empty():
    reg = CliAdapterRegistry.from_config({})
    assert support.select_single_cli({}, {}, reg) is None


# --------------------------------------------------------------------------- #
# Blueprint end-to-end (real subprocess)
# --------------------------------------------------------------------------- #

async def test_blueprint_runs_default_cli():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "ECHO: ping"
    # last chunk marked final
    assert chunks[-1].get("final") is True


async def test_blueprint_respects_cli_param():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    bp.set_params({"cli": "echo2"})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "TWO: ping"


async def test_blueprint_no_agents_configured():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config={})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert "No CLI agents are configured" in _final_content(chunks)


async def test_blueprint_empty_prompt():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    chunks = await _collect(bp.run([]))
    assert "No prompt provided" in _final_content(chunks)


async def test_blueprint_reports_cli_failure():
    cfg = {
        "cli_agents": {
            "boom": {"cmd": [PY, "-c", "import sys; sys.exit(2)", "{prompt}"]},
        },
        "cli_fusion": {"default_cli": "boom"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert "failed" in _final_content(chunks)
