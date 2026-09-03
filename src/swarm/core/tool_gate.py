"""Gate role: classify a pending tool call as dangerous or not.

Wiring is **default-open** (fail-open when unwired):

* No gate agent on the team → every tool call is approved and the user is
  **never** elicited.
* A ``gate`` / ``tool_gate`` role actually wired → the gate returns a
  single-token YES/NO (dangerous or not). Dangerous calls elicit user approval.

This is openai-agents handoff / agent-as-tool — not an extra Grok/OMB/Rakazo
seat. The Support agent (REQ-7) may *talk* about the gate; this module is the
runtime wiring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from swarm.core.agent_roles import (
    ROLE_GATE,
    attach_role,
    find_role_agent,
    normalize_agent_role,
)
from swarm.core.async_utils import run_coro_sync

logger = logging.getLogger(__name__)

GATE_ROLE = ROLE_GATE

GATE_INSTRUCTIONS = (
    "You are a tool-call gate. Classify the pending tool call as dangerous or not. "
    "Reply with a single token only: YES if the call is dangerous (destructive, "
    "irreversible, exfiltrating, privilege-escalating, or otherwise high-risk), "
    "NO if it is not. No punctuation, no explanation."
)

_DANGEROUS_TOKENS = frozenset({"YES", "Y", "DANGEROUS", "TRUE", "1"})
_SAFE_TOKENS = frozenset({"NO", "N", "SAFE", "FALSE", "0"})

ClassifyFn = Callable[[str, dict[str, Any]], bool]
ElicitFn = Callable[[str, dict[str, Any]], bool]
InvokeFn = Callable[[Any, str], str]


@dataclass
class GateVerdict:
    """Boolean danger classification plus the raw single-token reply."""

    dangerous: bool
    raw: str = ""
    elicited: bool = False
    approved: bool = True
    prompted: bool = False


@dataclass
class ToolGate:
    """Optional gate agent bound to a team. ``agent is None`` means unwired."""

    agent: Any = None
    classify_fn: ClassifyFn | None = None
    invoke_fn: InvokeFn | None = None
    elicit_fn: ElicitFn | None = None
    consultations: list[dict[str, Any]] = field(default_factory=list)

    @property
    def wired(self) -> bool:
        return self.agent is not None or self.classify_fn is not None

    def classify(self, tool_name: str, arguments: dict[str, Any] | None = None) -> GateVerdict:
        return classify_pending_tool_call(
            gate=self.agent,
            tool_name=tool_name,
            arguments=arguments,
            classify_fn=self.classify_fn,
            invoke_fn=self.invoke_fn,
            trace=self.consultations,
        )

    def approve(self, tool_name: str, arguments: dict[str, Any] | None = None) -> GateVerdict:
        return approve_pending_tool_call(
            gate=self.agent,
            tool_name=tool_name,
            arguments=arguments,
            classify_fn=self.classify_fn,
            invoke_fn=self.invoke_fn,
            elicit_fn=self.elicit_fn,
            trace=self.consultations,
        )


def parse_gate_token(text: Any) -> bool:
    """Parse a single-token (or equivalent structured) yes/no as *dangerous*."""
    if isinstance(text, bool):
        return text
    if isinstance(text, dict):
        for key in ("dangerous", "is_dangerous", "yes", "deny"):
            if key in text:
                return bool(text[key])
        if "approved" in text:
            return not bool(text["approved"])
        text = text.get("token") or text.get("answer") or text.get("content") or ""
    raw = str(text or "").strip()
    parts = raw.split()
    if not parts:
        return False
    token = parts[0].upper().strip(".,!?;:\"'")
    if token in _DANGEROUS_TOKENS:
        return True
    if token in _SAFE_TOKENS:
        return False
    # Ambiguous prose from a live model: not dangerous (do not fail closed).
    return False


def _gate_prompt(tool_name: str, arguments: dict[str, Any] | None) -> str:
    return (
        "Is this pending tool call dangerous?\n"
        f"Tool: {tool_name}\n"
        f"Arguments: {arguments or {}}\n"
        "Reply YES or NO only."
    )


def _invoke_gate_agent(
    gate: Any,
    prompt: str,
    *,
    invoke_fn: InvokeFn | None = None,
) -> str:
    """Consult the gate via injected fn, ``classify``, ``as_tool``, or Runner."""
    if invoke_fn is not None:
        return str(invoke_fn(gate, prompt))
    classify = getattr(gate, "classify", None)
    if callable(classify):
        return str(classify(prompt))
    respond = getattr(gate, "respond", None)
    if callable(respond):
        return str(respond(prompt))
    # openai-agents agent-as-tool: prefer a sync ``on_invoke_tool`` if present
    # after ``as_tool()``; otherwise try Runner (may be unavailable offline).
    as_tool = getattr(gate, "as_tool", None)
    if callable(as_tool):
        try:
            tool = as_tool(
                tool_name=getattr(gate, "name", None) or "gate",
                tool_description="Classify a pending tool call as dangerous or not.",
            )
            on_invoke = getattr(tool, "on_invoke_tool", None)
            if callable(on_invoke):
                result = on_invoke(None, prompt)
                if hasattr(result, "__await__"):
                    result = run_coro_sync(result)
                return str(result)
        except Exception as exc:
            logger.debug("gate as_tool invoke skipped: %s", exc)
    try:
        from agents import Runner

        async def _run() -> str:
            result = await Runner.run(gate, prompt, max_turns=1)
            return str(getattr(result, "final_output", None) or result)

        return run_coro_sync(_run())
    except Exception as exc:
        logger.info("gate Runner unavailable (%s); treating as unclassified", exc)
        raise


def classify_pending_tool_call(
    *,
    gate: Any = None,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    classify_fn: ClassifyFn | None = None,
    invoke_fn: InvokeFn | None = None,
    trace: list[dict[str, Any]] | None = None,
) -> GateVerdict:
    """Return whether *tool_name* is dangerous. Unwired → not dangerous."""
    args = arguments or {}
    if classify_fn is None and gate is None:
        verdict = GateVerdict(dangerous=False, raw="UNWIRED", approved=True)
        if trace is not None:
            trace.append({"tool": tool_name, "wired": False, "dangerous": False})
        return verdict
    raw = ""
    try:
        if classify_fn is not None:
            dangerous = bool(classify_fn(tool_name, args))
            raw = "YES" if dangerous else "NO"
        else:
            raw = _invoke_gate_agent(gate, _gate_prompt(tool_name, args), invoke_fn=invoke_fn)
            dangerous = parse_gate_token(raw)
    except Exception as exc:
        logger.info("wired gate failed to classify %s (%s); treating as dangerous", tool_name, exc)
        dangerous = True
        raw = f"ERROR: {exc}"
    verdict = GateVerdict(dangerous=dangerous, raw=str(raw))
    if trace is not None:
        trace.append({
            "tool": tool_name,
            "wired": True,
            "dangerous": dangerous,
            "raw": verdict.raw,
        })
    return verdict


def approve_pending_tool_call(
    *,
    gate: Any = None,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    classify_fn: ClassifyFn | None = None,
    invoke_fn: InvokeFn | None = None,
    elicit_fn: ElicitFn | None = None,
    trace: list[dict[str, Any]] | None = None,
) -> GateVerdict:
    """Approve a pending tool call.

    Unwired (no gate and no classify_fn): approved, **elicit_fn is not called**.
    Wired + not dangerous: approved, no prompt.
    Wired + dangerous: ``elicit_fn`` is called; missing elicit → denied.
    """
    args = arguments or {}
    unwired = gate is None and classify_fn is None
    if unwired:
        # Default-open: never prompt when no gate is wired to the team.
        verdict = GateVerdict(dangerous=False, raw="UNWIRED", approved=True, prompted=False)
        if trace is not None:
            trace.append({
                "tool": tool_name,
                "wired": False,
                "prompted": False,
                "approved": True,
            })
        return verdict

    classified = classify_pending_tool_call(
        gate=gate,
        tool_name=tool_name,
        arguments=args,
        classify_fn=classify_fn,
        invoke_fn=invoke_fn,
        trace=None,
    )
    if not classified.dangerous:
        classified.approved = True
        classified.prompted = False
        if trace is not None:
            trace.append({
                "tool": tool_name,
                "wired": True,
                "dangerous": False,
                "prompted": False,
                "approved": True,
                "raw": classified.raw,
            })
        return classified

    prompted = False
    approved = False
    if elicit_fn is not None:
        prompted = True
        approved = bool(elicit_fn(tool_name, args))
    classified.prompted = prompted
    classified.elicited = prompted
    classified.approved = approved
    if trace is not None:
        trace.append({
            "tool": tool_name,
            "wired": True,
            "dangerous": True,
            "prompted": prompted,
            "approved": approved,
            "raw": classified.raw,
        })
    return classified


def tool_gate_from_team(
    agents: Any,
    *,
    classify_fn: ClassifyFn | None = None,
    invoke_fn: InvokeFn | None = None,
    elicit_fn: ElicitFn | None = None,
) -> ToolGate:
    """Build a ``ToolGate`` from a team roster. Missing gate → unwired."""
    return ToolGate(
        agent=find_role_agent(agents, ROLE_GATE),
        classify_fn=classify_fn,
        invoke_fn=invoke_fn,
        elicit_fn=elicit_fn,
    )


def attach_gate_as_tool(coordinator: Any, gate: Any) -> Any:
    """Expose the gate on the coordinator via openai-agents ``as_tool``.

    Classification still goes through :func:`approve_pending_tool_call` so a
    coordinator that forgets to call the tool cannot bypass the wrapper path.
    """
    if coordinator is None or gate is None:
        return coordinator
    attach_role(gate, ROLE_GATE)
    as_tool = getattr(gate, "as_tool", None)
    if not callable(as_tool):
        return coordinator
    try:
        tool = as_tool(
            tool_name=getattr(gate, "name", None) or "gate",
            tool_description=(
                "Classify a pending tool call as dangerous (YES) or not (NO). "
                "Single-token reply."
            ),
        )
        tools = list(getattr(coordinator, "tools", None) or [])
        tools.append(tool)
        coordinator.tools = tools
    except Exception as exc:
        logger.debug("gate as_tool wiring skipped: %s", exc)
    return coordinator


def gate_wrap_callable(
    fn: Callable[..., Any],
    *,
    tool_name: str,
    gate: Any = None,
    classify_fn: ClassifyFn | None = None,
    invoke_fn: InvokeFn | None = None,
    elicit_fn: ElicitFn | None = None,
    trace: list[dict[str, Any]] | None = None,
) -> Callable[..., Any]:
    """Wrap a callable so a wired gate classifies it before it runs.

    Unwired gate: the wrapper is a no-op passthrough (still no elicit).
    """
    if gate is None and classify_fn is None:
        return fn

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        verdict = approve_pending_tool_call(
            gate=gate,
            tool_name=tool_name,
            arguments={"args": args, "kwargs": kwargs},
            classify_fn=classify_fn,
            invoke_fn=invoke_fn,
            elicit_fn=elicit_fn,
            trace=trace,
        )
        if not verdict.approved:
            return f"DENIED: tool call {tool_name!r} was not approved"
        return fn(*args, **kwargs)

    wrapped.__name__ = getattr(fn, "__name__", tool_name)
    wrapped.__doc__ = getattr(fn, "__doc__", None)
    return wrapped


def wrap_tools_with_gate(
    tools: list[Any] | None,
    *,
    gate: Any = None,
    classify_fn: ClassifyFn | None = None,
    invoke_fn: InvokeFn | None = None,
    elicit_fn: ElicitFn | None = None,
    trace: list[dict[str, Any]] | None = None,
) -> list[Any]:
    """Wrap a list of callables. Unwired → returned unchanged (no prompt)."""
    if not tools:
        return list(tools or [])
    if gate is None and classify_fn is None:
        return list(tools)
    wrapped: list[Any] = []
    for tool in tools:
        name = (
            getattr(tool, "name", None)
            or getattr(tool, "__name__", None)
            or type(tool).__name__
        )
        if callable(tool) and not hasattr(tool, "on_invoke_tool"):
            wrapped.append(
                gate_wrap_callable(
                    tool,
                    tool_name=str(name),
                    gate=gate,
                    classify_fn=classify_fn,
                    invoke_fn=invoke_fn,
                    elicit_fn=elicit_fn,
                    trace=trace,
                )
            )
        else:
            wrapped.append(tool)
    return wrapped


def is_gate_role(role: Any) -> bool:
    return normalize_agent_role(role) == ROLE_GATE
