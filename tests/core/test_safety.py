"""REQ-55 Safety: default-open, prompt-on-concern, always-allow, CLI/remote skip."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

from swarm.core.cli_adapter import CliAdapter
from swarm.core.cli_tools import cli_persona
from swarm.core.safety import (
    CHANNEL_API,
    CHANNEL_CLI,
    CHANNEL_REMOTE,
    AlwaysAllowStore,
    approve_pending_tool_call,
    channel_for_runtime,
    classify_pending_tool_call,
    parse_safety_token,
    safety_role_assigned,
    uses_swarm_approval,
    wrap_tools_with_safety,
)
from swarm.herdr.client import HerdrBlockedError, HerdrClient


def test_parse_safety_token_yes_no_and_empty():
    assert parse_safety_token("YES") is True
    assert parse_safety_token("NO") is False
    assert parse_safety_token("yes, because rm") is True
    assert parse_safety_token({"concerned": True}) is True
    assert parse_safety_token({"approved": True}) is False
    assert parse_safety_token("") is False
    assert parse_safety_token("   ") is False


def test_unwired_safety_does_not_prompt():
    prompted: list[tuple[str, dict]] = []

    def elicit(name: str, args: dict) -> bool:
        prompted.append((name, args))
        return False

    verdict = approve_pending_tool_call(
        channel=CHANNEL_API,
        tool_name="execute_shell_command",
        arguments={"command": "rm -rf /"},
        elicit_fn=elicit,
        safety_assigned=False,
    )
    assert verdict.approved is True
    assert verdict.prompted is False
    assert verdict.concerned is False
    assert prompted == []


def test_unwired_classify_is_not_concerned():
    verdict = classify_pending_tool_call(tool_name="write_file", safety_assigned=False)
    assert verdict.concerned is False
    assert verdict.raw == "UNWIRED"


def test_wired_unconcerned_does_not_prompt():
    prompted: list[str] = []

    def elicit(name: str, _args: dict) -> bool:
        prompted.append(name)
        return False

    verdict = approve_pending_tool_call(
        safety=object(),
        tool_name="read_file",
        classify_fn=lambda _n, _a: False,
        elicit_fn=elicit,
        safety_assigned=True,
    )
    assert verdict.approved is True
    assert verdict.concerned is False
    assert verdict.prompted is False
    assert prompted == []


def test_wired_concerned_elicits():
    prompted: list[str] = []

    def elicit(name: str, _args: dict) -> str:
        prompted.append(name)
        return "allow"

    verdict = approve_pending_tool_call(
        safety=object(),
        tool_name="execute_shell_command",
        classify_fn=lambda _n, _a: True,
        elicit_fn=elicit,
        safety_assigned=True,
    )
    assert verdict.concerned is True
    assert verdict.prompted is True
    assert verdict.approved is True
    assert prompted == ["execute_shell_command"]


def test_wired_concerned_deny():
    verdict = approve_pending_tool_call(
        safety=object(),
        tool_name="wipe",
        classify_fn=lambda _n, _a: True,
        elicit_fn=lambda _n, _a: "deny",
        safety_assigned=True,
    )
    assert verdict.approved is False
    assert verdict.prompted is True


def test_always_allow_skips_next_prompt(tmp_path: Path):
    store = AlwaysAllowStore(path=tmp_path / "always.json")
    prompted: list[str] = []

    def elicit(name: str, _args: dict) -> str:
        prompted.append(name)
        return "always"

    first = approve_pending_tool_call(
        safety=object(),
        tool_name="write_file",
        agent_id="codey",
        classify_fn=lambda _n, _a: True,
        elicit_fn=elicit,
        always_allow=store,
        safety_assigned=True,
    )
    assert first.approved is True
    assert first.prompted is True
    assert store.is_allowed("codey", "write_file")

    second = approve_pending_tool_call(
        safety=object(),
        tool_name="write_file",
        agent_id="codey",
        classify_fn=lambda _n, _a: True,
        elicit_fn=elicit,
        always_allow=store,
        safety_assigned=True,
    )
    assert second.approved is True
    assert second.prompted is False
    assert second.always_allowed is True
    assert prompted == ["write_file"]


def test_always_allow_is_per_agent(tmp_path: Path):
    store = AlwaysAllowStore(path=tmp_path / "always.json")
    store.allow("codey", "write_file")
    prompted: list[str] = []
    verdict = approve_pending_tool_call(
        safety=object(),
        tool_name="write_file",
        agent_id="stewie",
        classify_fn=lambda _n, _a: True,
        elicit_fn=lambda n, _a: prompted.append(n) or "deny",
        always_allow=store,
        safety_assigned=True,
    )
    assert verdict.prompted is True
    assert prompted == ["write_file"]


def test_cli_and_remote_channels_do_not_call_elicit():
    prompted: list[str] = []

    def elicit(name: str, _args: dict) -> bool:
        prompted.append(name)
        return False

    for channel in (CHANNEL_CLI, CHANNEL_REMOTE):
        verdict = approve_pending_tool_call(
            channel=channel,
            safety=object(),
            tool_name="execute_shell_command",
            classify_fn=lambda _n, _a: True,
            elicit_fn=elicit,
            safety_assigned=True,
        )
        assert verdict.approved is True
        assert verdict.prompted is False
        assert verdict.raw == "CHANNEL_SKIP"
        assert uses_swarm_approval(channel) is False
    assert prompted == []


def test_cli_remote_wrap_is_identity():
    def boom() -> str:
        return "ran"

    for channel in (CHANNEL_CLI, CHANNEL_REMOTE):
        wrapped = wrap_tools_with_safety(
            [boom],
            channel=channel,
            safety=object(),
            classify_fn=lambda _n, _a: True,
            elicit_fn=lambda _n, _a: False,
            safety_assigned=True,
        )
        assert wrapped[0] is boom
        assert wrapped[0]() == "ran"


def test_channel_for_runtime_maps_cli_and_remote():
    assert channel_for_runtime(blueprint_id="codey") == CHANNEL_API
    assert channel_for_runtime(blueprint_id="cli_agent") == CHANNEL_CLI
    assert channel_for_runtime(blueprint_id="cli_fusion") == CHANNEL_CLI
    assert channel_for_runtime(blueprint_id="remote_harness") == CHANNEL_REMOTE
    assert channel_for_runtime(member_kind="herdr") == CHANNEL_REMOTE
    assert channel_for_runtime(member_kind="cli") == CHANNEL_CLI


def test_safety_role_assigned_aliases():
    assert safety_role_assigned([{"name": "Writer", "role": "default"}]) is False
    assert safety_role_assigned([{"name": "ToolGate", "role": "tool_gate"}]) is True
    assert safety_role_assigned([{"name": "Safety", "role": "safety"}]) is True
    assert safety_role_assigned(metadata={"gate_agent": "Gate"}) is True
    assert safety_role_assigned(metadata={"role": "gate"}) is True


async def test_cli_persona_path_does_not_call_swarm_approval(monkeypatch):
    """Shipped CLI adapter path must not invoke swarm Safety elicit."""
    calls: list[str] = []

    def forbidden(*_a, **_k):
        calls.append("approve")
        raise AssertionError("CLI path must not call swarm approval")

    monkeypatch.setattr("swarm.core.safety.approve_pending_tool_call", forbidden)
    adapter = CliAdapter.from_config(
        "echo",
        {"cmd": [sys.executable, "-c", "import sys; print(sys.argv[1])", "{prompt}"]},
    )
    ask = cli_persona(adapter)
    out = await ask("hi")
    assert "hi" in out
    assert calls == []


def test_herdr_remote_path_does_not_call_swarm_approval(monkeypatch):
    """Remote Herdr keeps its own blocked/approval UI; swarm must not elicit."""
    calls: list[str] = []

    def forbidden(*_a, **_k):
        calls.append("approve")
        raise AssertionError("remote path must not call swarm approval")

    monkeypatch.setattr("swarm.core.safety.approve_pending_tool_call", forbidden)

    def runner(argv, **_kwargs):
        result = MagicMock()
        result.returncode = 1
        result.stdout = '{"type": "agent_blocked", "code": "agent_blocked"}'
        result.stderr = "agent_blocked"
        return result

    client = HerdrClient(remote="", runner=runner)
    try:
        client.agent_prompt("w3:p1", "hello")
    except HerdrBlockedError:
        pass
    assert calls == []
    assert uses_swarm_approval(channel_for_runtime(member_kind="herdr")) is False
