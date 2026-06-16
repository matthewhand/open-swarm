"""Tests for the agent-tool layer (swarm.core.cli_tools)."""

from __future__ import annotations

import sys

from swarm.core.cli_adapter import CliAdapter
from swarm.core.cli_tools import as_function_tool, cli_persona, consensus_fn

PY = sys.executable


def _echo(name: str) -> CliAdapter:
    return CliAdapter.from_config(
        name, {"cmd": [PY, "-c", f"import sys; print('{name}:' + sys.argv[1])", "{prompt}"]}
    )


def _judge() -> CliAdapter:
    return CliAdapter.from_config(
        "judge", {"cmd": [PY, "-c", "print('{\"answer\": \"AGREED\", \"done\": true}')", "{prompt}"]}
    )


async def test_cli_persona_returns_answer():
    ask = cli_persona(_echo("claude"))
    assert await ask("hi") == "claude:hi"


async def test_cli_persona_reports_failure_without_raising():
    boom = CliAdapter.from_config("boom", {"cmd": [PY, "-c", "import sys; sys.exit(1)", "{prompt}"]})
    out = await cli_persona(boom)("hi")
    assert out.startswith("[boom unavailable:")


def test_cli_persona_tool_name_is_safe_identifier():
    ask = cli_persona(_echo("gpt-4o cli"))
    assert ask.__name__ == "ask_gpt_4o_cli"


async def test_consensus_fn_returns_judged_answer():
    fn = consensus_fn([_echo("a"), _echo("b")], _judge())
    assert await fn("q") == "AGREED"


async def test_consensus_fn_all_fail_message():
    boom = CliAdapter.from_config("boom", {"cmd": [PY, "-c", "import sys; sys.exit(1)", "{prompt}"]})
    assert await consensus_fn([boom])("q") == "(no consensus reached)"


def test_as_function_tool_builds_named_tool():
    tool = as_function_tool(cli_persona(_echo("claude")), name="ask_claude")
    # openai-agents FunctionTool exposes a .name; the wrap should succeed and name it.
    assert getattr(tool, "name", None) == "ask_claude"
