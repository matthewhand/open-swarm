"""REQ-108: classifier verdict is a tool call, not parsed prose."""

from __future__ import annotations

from swarm.core.classifier_verdict import (
    DEFAULT_CLASSIFIER_NUDGES,
    GATE_INSTRUCTIONS,
    GATE_VERDICT_TOOL,
    SKEPTIC_INSTRUCTIONS,
    SKEPTIC_VERDICT_TOOL,
    ClassifierTurnResult,
    attach_classifier_tools,
    classifier_ui_label,
    continue_nudge,
    ensure_classifier_instructions,
    extract_verdict_tool_call,
    run_classifier_until_verdict,
    spec_for_role,
    submit_gate_verdict,
    submit_skeptic_verdict,
)
from swarm.core.skeptic import SKEPTIC_INSTRUCTIONS as SKEPTIC_REEXPORT
from swarm.core.tool_gate import (
    GATE_INSTRUCTIONS as GATE_REEXPORT,
    classify_pending_tool_call,
)


def test_default_role_instructions_name_the_verdict_tool():
    assert GATE_VERDICT_TOOL in GATE_INSTRUCTIONS
    assert "MUST call" in GATE_INSTRUCTIONS
    assert 'verdict="yes"' in GATE_INSTRUCTIONS
    assert GATE_VERDICT_TOOL in GATE_REEXPORT
    assert SKEPTIC_VERDICT_TOOL in SKEPTIC_INSTRUCTIONS
    assert "MUST call" in SKEPTIC_INSTRUCTIONS
    assert 'verdict="pass"' in SKEPTIC_INSTRUCTIONS
    assert SKEPTIC_VERDICT_TOOL in SKEPTIC_REEXPORT
    assert spec_for_role("tool_gate").tool_name == GATE_VERDICT_TOOL
    assert spec_for_role("safety").tool_name == GATE_VERDICT_TOOL


def test_ensure_classifier_instructions_reappends_close_line():
    custom = "Look at the shell command and think about rollback."
    ensured = ensure_classifier_instructions(custom, "gate")
    assert custom in ensured
    assert GATE_VERDICT_TOOL in ensured
    already = ensure_classifier_instructions(
        f"Investigate freely. Then call `{GATE_VERDICT_TOOL}`.",
        "gate",
    )
    assert already.count(GATE_VERDICT_TOOL) == 1
    assert ensure_classifier_instructions("", "skeptic") == SKEPTIC_INSTRUCTIONS


def test_prose_is_nudged_then_tool_call_is_accepted():
    turns: list[str] = []

    def invoke(_agent, message: str) -> str:
        turns.append(message)
        if len(turns) == 1:
            return "YES this is dangerous because it deletes files"
        submit_gate_verdict(verdict="yes", reason="destructive delete")
        return "recorded"

    result = run_classifier_until_verdict(
        agent=type("Gate", (), {"name": "gate"})(),
        prompt="Classify rm -rf /tmp/x",
        role="gate",
        invoke_fn=invoke,
    )
    assert result.accepted is True
    assert result.failed_closed is False
    assert result.nudges == 1
    assert result.payload is not None
    assert result.payload["dangerous"] is True
    assert result.payload["verdict"] == "yes"
    assert GATE_VERDICT_TOOL in turns[1]
    assert "Nudged classifier (1/3)" in turns[1]
    assert "YES this is dangerous" not in (result.raw or "")


def test_never_calls_after_n_fail_closed_for_gate():
    def invoke(_agent, _message: str) -> str:
        return "NO it looks fine"

    result = run_classifier_until_verdict(
        agent=object(),
        prompt="Classify read_file",
        role="gate",
        invoke_fn=invoke,
        max_nudges=2,
    )
    assert result.accepted is False
    assert result.failed_closed is True
    assert result.nudges == 2
    assert result.payload is not None
    assert result.payload["dangerous"] is True
    assert result.payload["needs_human"] is True
    assert result.payload["verdict"] == "yes"
    assert "FAIL_CLOSED" in (result.error or "")
    assert GATE_VERDICT_TOOL in (result.error or "")
    assert "not parsed" in (result.error or "")
    assert result.phase == "fail_closed"


def test_never_calls_after_n_fail_closed_for_skeptic():
    def invoke(_agent, _message: str) -> str:
        return "PASS — the file is clearly there"

    result = run_classifier_until_verdict(
        agent=object(),
        prompt="Was summary.md written?",
        role="skeptic",
        invoke_fn=invoke,
        max_nudges=DEFAULT_CLASSIFIER_NUDGES,
    )
    assert result.failed_closed is True
    assert result.payload is not None
    assert result.payload["accomplished"] is False
    assert result.payload["verdict"] == "fail"
    assert SKEPTIC_VERDICT_TOOL in (result.error or "")
    assert result.nudges == DEFAULT_CLASSIFIER_NUDGES


def test_first_turn_tool_call_is_accepted_with_no_nudge():
    def invoke(_agent, message: str) -> dict:
        assert "Nudged classifier" not in message
        return {
            "tool_calls": [
                {
                    "name": SKEPTIC_VERDICT_TOOL,
                    "arguments": {"verdict": "pass", "reason": "file exists"},
                }
            ]
        }

    result = run_classifier_until_verdict(
        agent=object(),
        prompt="Review the work",
        role="skeptic",
        invoke_fn=invoke,
    )
    assert result.accepted is True
    assert result.nudges == 0
    assert result.nudge_messages == []
    assert result.payload is not None
    assert result.payload["accomplished"] is True
    assert result.payload["verdict"] == "pass"


def test_extract_verdict_ignores_prose_and_reads_tool_calls():
    assert extract_verdict_tool_call("YES", GATE_VERDICT_TOOL) is None
    assert extract_verdict_tool_call({"content": "NO"}, GATE_VERDICT_TOOL) is None
    args = extract_verdict_tool_call(
        {
            "tool_calls": [
                {"name": GATE_VERDICT_TOOL, "arguments": {"verdict": "no", "reason": "read only"}}
            ]
        },
        GATE_VERDICT_TOOL,
    )
    assert args == {"verdict": "no", "reason": "read only"}


def test_continue_nudge_and_ui_labels_name_the_tool():
    text = continue_nudge(GATE_VERDICT_TOOL, 2, 3)
    assert GATE_VERDICT_TOOL in text
    assert "Nudged classifier (2/3)" in text
    assert classifier_ui_label("waiting") == "Waiting for verdict…"
    assert classifier_ui_label("nudged", 2, 3) == "Nudged classifier (2/3)"
    assert "failed closed" in classifier_ui_label("fail_closed").lower()


def test_wired_gate_prose_is_not_parsed_as_safe():
    """A wired gate that only writes NO must fail closed, not parse prose."""

    def invoke(_agent, _message: str) -> str:
        return "NO"

    verdict = classify_pending_tool_call(
        gate=object(),
        tool_name="wipe",
        invoke_fn=invoke,
    )
    assert verdict.dangerous is True
    assert verdict.failed_closed is True
    assert verdict.needs_human is True
    assert GATE_VERDICT_TOOL in verdict.raw


def test_wired_gate_tool_call_is_accepted():
    def invoke(_agent, _message: str) -> str:
        submit_gate_verdict(verdict="no", reason="read-only path")
        return "done"

    verdict = classify_pending_tool_call(
        gate=object(),
        tool_name="read_file",
        invoke_fn=invoke,
    )
    assert verdict.dangerous is False
    assert verdict.failed_closed is False
    assert verdict.nudges == 0
    assert verdict.reason == "read-only path"


def test_attach_classifier_tools_stamps_instructions_and_tool_name():
    agent = type("Agent", (), {"tools": [], "instructions": "Be careful."})()
    attach_classifier_tools(agent, "gate")
    assert GATE_VERDICT_TOOL in agent.instructions
    names = {getattr(t, "name", None) or getattr(t, "__name__", None) for t in agent.tools}
    assert GATE_VERDICT_TOOL in names


def test_register_classifier_role_is_extensible():
    from swarm.core.classifier_verdict import (
        CLASSIFIER_SPECS,
        ClassifierSpec,
        register_classifier_role,
    )

    spec = register_classifier_role(
        ClassifierSpec(
            role="audit",
            tool_name="submit_audit_verdict",
            close_line="When done, call `submit_audit_verdict`.",
            instructions="You are an auditor. When done, call `submit_audit_verdict`.",
            fail_closed_kind="skeptic",
        )
    )
    try:
        assert spec_for_role("audit").tool_name == "submit_audit_verdict"
        text = continue_nudge(spec.tool_name, 1, 3)
        assert "submit_audit_verdict" in text
    finally:
        CLASSIFIER_SPECS.pop("audit", None)


def test_classifier_turn_result_ui_label():
    result = ClassifierTurnResult(
        accepted=False,
        failed_closed=True,
        payload=None,
        nudges=3,
        phase="fail_closed",
        tool_name=GATE_VERDICT_TOOL,
        role="gate",
    )
    assert "failed closed" in result.ui_label.lower()
