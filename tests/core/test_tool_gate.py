"""Gate role: default-open when unwired; elicit only on wired+dangerous."""

from swarm.core.tool_gate import (
    GATE_INSTRUCTIONS,
    approve_pending_tool_call,
    classify_pending_tool_call,
    gate_wrap_callable,
    parse_gate_token,
    tool_gate_from_team,
    wrap_tools_with_gate,
)


def test_parse_gate_token_single_token_and_structured():
    assert parse_gate_token("YES") is True
    assert parse_gate_token("NO") is False
    assert parse_gate_token("yes, because rm -rf") is True
    assert parse_gate_token({"dangerous": True}) is True
    assert parse_gate_token({"approved": True}) is False
    assert parse_gate_token("") is False


def test_unwired_gate_does_not_prompt():
    """Success criterion: unwired team never elicits, all calls approved."""
    prompted: list[tuple[str, dict]] = []

    def elicit(name: str, args: dict) -> bool:
        prompted.append((name, args))
        return False

    verdict = approve_pending_tool_call(
        gate=None,
        tool_name="execute_shell_command",
        arguments={"command": "rm -rf /"},
        elicit_fn=elicit,
    )
    assert verdict.approved is True
    assert verdict.prompted is False
    assert prompted == []


def test_unwired_classify_is_not_dangerous():
    verdict = classify_pending_tool_call(gate=None, tool_name="write_file")
    assert verdict.dangerous is False
    assert verdict.raw == "UNWIRED"


def test_unwired_wrap_is_identity_and_does_not_prompt():
    prompted: list[str] = []

    def elicit(name: str, _args: dict) -> bool:
        prompted.append(name)
        return False

    def boom() -> str:
        return "ran"

    wrapped = wrap_tools_with_gate([boom], gate=None, elicit_fn=elicit)
    assert wrapped[0] is boom
    assert wrapped[0]() == "ran"
    assert prompted == []


def test_wired_safe_call_does_not_elicit():
    prompted: list[str] = []

    def elicit(name: str, _args: dict) -> bool:
        prompted.append(name)
        return False

    verdict = approve_pending_tool_call(
        gate=object(),
        tool_name="read_file",
        arguments={"path": "notes.txt"},
        classify_fn=lambda _n, _a: False,
        elicit_fn=elicit,
    )
    assert verdict.approved is True
    assert verdict.dangerous is False
    assert verdict.prompted is False
    assert prompted == []


def test_wired_dangerous_call_elicits():
    prompted: list[str] = []

    def elicit(name: str, _args: dict) -> bool:
        prompted.append(name)
        return True

    verdict = approve_pending_tool_call(
        gate=object(),
        tool_name="execute_shell_command",
        arguments={"command": "rm -rf /tmp/x"},
        classify_fn=lambda _n, _a: True,
        elicit_fn=elicit,
    )
    assert verdict.dangerous is True
    assert verdict.prompted is True
    assert verdict.approved is True
    assert prompted == ["execute_shell_command"]


def test_wired_dangerous_without_elicit_is_denied():
    verdict = approve_pending_tool_call(
        gate=object(),
        tool_name="wipe",
        classify_fn=lambda _n, _a: True,
        elicit_fn=None,
    )
    assert verdict.dangerous is True
    assert verdict.approved is False
    assert verdict.prompted is False


def test_wired_user_rejects_dangerous_call():
    verdict = approve_pending_tool_call(
        gate=object(),
        tool_name="wipe",
        classify_fn=lambda _n, _a: True,
        elicit_fn=lambda _n, _a: False,
    )
    assert verdict.approved is False
    assert verdict.prompted is True


def test_gate_wrap_callable_blocks_when_denied():
    def write_file(path: str) -> str:
        return f"wrote {path}"

    wrapped = gate_wrap_callable(
        write_file,
        tool_name="write_file",
        gate=object(),
        classify_fn=lambda _n, _a: True,
        elicit_fn=lambda _n, _a: False,
    )
    assert wrapped("secret.txt").startswith("DENIED")


def test_tool_gate_from_team_unwired_vs_wired():
    team = [
        {"name": "Writer", "role": "default"},
        {"name": "ToolGate", "role": "tool_gate"},
    ]
    unwired = tool_gate_from_team([{"name": "Writer", "role": "default"}])
    assert unwired.wired is False
    wired = tool_gate_from_team(team)
    assert wired.wired is True
    assert wired.agent["name"] == "ToolGate"


def test_invoke_fn_single_token_yes():
    gate = type("GateAgent", (), {"name": "gate", "role": "gate"})()
    verdict = classify_pending_tool_call(
        gate=gate,
        tool_name="shell",
        invoke_fn=lambda _agent, _prompt: "YES",
    )
    assert verdict.dangerous is True
    assert "YES" in GATE_INSTRUCTIONS or "single token" in GATE_INSTRUCTIONS.lower()
