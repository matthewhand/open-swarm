"""Tests for the CLI agent adapter layer (swarm.core.cli_adapter).

These exercise real subprocesses using the running Python interpreter as a
stand-in agentic CLI, so they verify the actual launch/lifecycle/parse path
rather than a mock.
"""

from __future__ import annotations

import asyncio
import sys
import time

import pytest

from swarm.core.cli_adapter import (
    CliAdapter,
    CliAdapterError,
    CliAdapterRegistry,
    CliAgentConfig,
)

PY = sys.executable


def _echo_cfg(**over) -> dict:
    # Echo the prompt back, prefixed, via argv injection.
    base = {
        "cmd": [PY, "-c", "import sys; print('ECHO: ' + sys.argv[1])", "{prompt}"],
        "parse": "text",
    }
    base.update(over)
    return base


# --------------------------------------------------------------------------- #
# Config validation
# --------------------------------------------------------------------------- #

def test_empty_cmd_rejected():
    with pytest.raises(CliAdapterError):
        CliAgentConfig(name="x", cmd=[])


def test_arg_mode_requires_prompt_token():
    with pytest.raises(CliAdapterError):
        CliAgentConfig(name="x", cmd=[PY, "-c", "print(1)"])  # no {prompt}


def test_stdin_mode_does_not_require_prompt_token():
    cfg = CliAgentConfig(name="x", cmd=["cat"], prompt_mode="stdin")
    assert cfg.prompt_mode == "stdin"


def test_bad_prompt_mode_rejected():
    with pytest.raises(CliAdapterError):
        CliAgentConfig(name="x", cmd=["cat", "{prompt}"], prompt_mode="bogus")


# --------------------------------------------------------------------------- #
# Run: happy paths
# --------------------------------------------------------------------------- #

async def test_arg_mode_text():
    adapter = CliAdapter.from_config("echo", _echo_cfg())
    res = await adapter.run("hello world")
    assert res.ok is True
    assert res.text == "ECHO: hello world"
    assert res.returncode == 0
    assert res.parse_error is None


async def test_stdin_mode():
    adapter = CliAdapter.from_config(
        "cat", {"cmd": ["cat"], "prompt_mode": "stdin", "parse": "text"}
    )
    res = await adapter.run("piped prompt")
    assert res.ok is True
    assert res.text == "piped prompt"


async def test_json_parse_dotpath():
    code = "import json,sys; print(json.dumps({'result': 'answer:' + sys.argv[1]}))"
    adapter = CliAdapter.from_config(
        "j", {"cmd": [PY, "-c", code, "{prompt}"], "parse": "json:.result"}
    )
    res = await adapter.run("Q")
    assert res.ok is True
    assert res.text == "answer:Q"
    assert res.parse_error is None


async def test_json_parse_nested_list_index():
    code = (
        "import json; "
        "print(json.dumps({'choices':[{'message':{'content':'deep'}}]}))"
    )
    adapter = CliAdapter.from_config(
        "j",
        {"cmd": [PY, "-c", code, "{prompt}"], "parse": "json:.choices.0.message.content"},
    )
    res = await adapter.run("ignored")
    assert res.ok is True
    assert res.text == "deep"


async def test_json_parse_failure_falls_back_to_raw():
    adapter = CliAdapter.from_config(
        "j", {"cmd": [PY, "-c", "print('not json')", "{prompt}"], "parse": "json:.result"}
    )
    res = await adapter.run("Q")
    # Still "ok" (process succeeded); parse_error records the problem.
    assert res.ok is True
    assert res.parse_error is not None
    assert res.text == "not json"


# --------------------------------------------------------------------------- #
# Run: failure modes
# --------------------------------------------------------------------------- #

async def test_nonzero_exit_is_not_ok():
    code = "import sys; sys.stderr.write('boom'); sys.exit(3)"
    adapter = CliAdapter.from_config("f", {"cmd": [PY, "-c", code, "{prompt}"]})
    res = await adapter.run("x")
    assert res.ok is False
    assert res.returncode == 3
    assert "boom" in (res.error or "")


async def test_missing_executable_is_not_ok():
    adapter = CliAdapter.from_config(
        "missing", {"cmd": ["this-cli-does-not-exist-xyz", "{prompt}"]}
    )
    res = await adapter.run("x")
    assert res.ok is False
    assert "not found" in (res.error or "")


async def test_timeout_kills_and_reports():
    # Sleep far longer than the timeout; must come back quickly as timed_out.
    code = "import time; time.sleep(30)"
    adapter = CliAdapter.from_config(
        "slow", {"cmd": [PY, "-c", code, "{prompt}"], "timeout": 0.4}
    )
    start = time.monotonic()
    res = await adapter.run("x")
    elapsed = time.monotonic() - start
    assert res.ok is False
    assert res.timed_out is True
    # Should be killed shortly after the 0.4s timeout, not run for 30s.
    assert elapsed < 10


async def test_extra_env_passed_through():
    code = "import os,sys; print(os.environ.get('SWARM_TEST_VAR', 'unset'))"
    adapter = CliAdapter.from_config("e", {"cmd": [PY, "-c", code, "{prompt}"]})
    res = await adapter.run("x", extra_env={"SWARM_TEST_VAR": "present"})
    assert res.ok is True
    assert res.text == "present"


# --------------------------------------------------------------------------- #
# Parallel panel semantics
# --------------------------------------------------------------------------- #

async def test_parallel_panel_gather():
    adapters = [CliAdapter.from_config(f"a{i}", _echo_cfg()) for i in range(4)]
    results = await asyncio.gather(*(a.run(f"p{i}") for i, a in enumerate(adapters)))
    assert [r.text for r in results] == [f"ECHO: p{i}" for i in range(4)]
    assert all(r.ok for r in results)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def test_registry_from_config_and_lookup():
    reg = CliAdapterRegistry.from_config(
        {"cli_agents": {"echo": _echo_cfg(), "cat": {"cmd": ["cat"], "prompt_mode": "stdin"}}}
    )
    assert reg.names() == ["cat", "echo"]
    assert reg.get("echo").name == "echo"
    with pytest.raises(CliAdapterError):
        reg.get("nope")


def test_registry_skips_invalid_adapters():
    reg = CliAdapterRegistry.from_config(
        {"cli_agents": {"good": _echo_cfg(), "bad": {"cmd": []}}}
    )
    assert reg.names() == ["good"]


def test_registry_available_filters_missing():
    reg = CliAdapterRegistry.from_config(
        {
            "cli_agents": {
                "real": _echo_cfg(),
                "ghost": {"cmd": ["definitely-not-a-real-cli-zzz", "{prompt}"]},
            }
        }
    )
    avail = reg.available()
    assert "real" in avail
    assert "ghost" not in avail


def test_registry_resolve_panel():
    reg = CliAdapterRegistry.from_config({"cli_agents": {"a": _echo_cfg(), "b": _echo_cfg()}})
    panel = reg.resolve_panel(["a", "b"])
    assert [a.name for a in panel] == ["a", "b"]


def test_with_overrides_is_non_mutating():
    reg = CliAdapterRegistry.from_config({"cli_agents": {"echo": _echo_cfg(timeout=5)}})
    reg2 = reg.with_overrides({"echo": {"timeout": 99}})
    assert reg.get("echo").config.timeout == 5
    assert reg2.get("echo").config.timeout == 99
