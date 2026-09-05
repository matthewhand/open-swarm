"""REQ-108 — classifier roles finish via a dedicated verdict tool.

Roles that return a yes/no-ish determination (gate, skeptic, similar) may
investigate with any tools, then **must** call a named verdict tool to stop.
The runtime never scrapes YES/NO/PASS/FAIL from free-text prose.

If generation ends without that tool call, the runtime auto-injects a short
continue nudge that repeats the tool name, up to ``N`` times (default **3**,
overridable via ``max_nudges`` or ``SWARM_CLASSIFIER_NUDGES``). Each nudge is
logged.

After the nudge budget is exhausted without a verdict tool call (**fail closed**):

* **gate** (and safety): ``dangerous=True`` / ``needs_human=True``. The pending
  tool is **blocked** (``approved=False``) unless an elicit callback explicitly
  approves — that is the needs-human path. Distinct from the *unwired* gate
  fail-open rule (no gate on the roster → approve, never prompt).
* **skeptic**: ``FAIL`` (``accomplished=False``). Findings state that
  ``submit_skeptic_verdict`` was not called. Honest error, not a guessed PASS.

Role instructions **must** name the exact tool. Custom user text may add
investigation guidance; :func:`ensure_classifier_instructions` re-appends the
mandatory close line when the tool name is missing.
"""

from __future__ import annotations

import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from swarm.core.async_utils import run_coro_sync

logger = logging.getLogger(__name__)

DEFAULT_CLASSIFIER_NUDGES = 3
NUDGE_ENV = "SWARM_CLASSIFIER_NUDGES"

GATE_VERDICT_TOOL = "submit_gate_verdict"
SKEPTIC_VERDICT_TOOL = "submit_skeptic_verdict"

GATE_CLOSE_LINE = (
    "When done, you MUST call `submit_gate_verdict` to finish. "
    "Arguments: verdict=\"yes\" if the pending tool call is dangerous "
    "(destructive, irreversible, exfiltrating, privilege-escalating, or "
    "otherwise high-risk), or verdict=\"no\" if it is not. Optional reason. "
    "Example: submit_gate_verdict(verdict=\"yes\", reason=\"destructive rm -rf\"). "
    "Prose alone is not a verdict — never finish by writing YES/NO in chat."
)

SKEPTIC_CLOSE_LINE = (
    "When done, you MUST call `submit_skeptic_verdict` to finish. "
    "Arguments: verdict=\"pass\" if the original agent accomplished the prompt, "
    "or verdict=\"fail\" if it did not. Optional reason (findings for a retry) "
    "and optional checks. "
    "Example: submit_skeptic_verdict(verdict=\"fail\", reason=\"summary.md was not written\"). "
    "Prose alone is not a verdict — never finish by writing PASS/FAIL or YES/NO in chat."
)

GATE_INSTRUCTIONS = (
    "You are a tool-call gate. Classify the pending tool call as dangerous or not. "
    "You may inspect context or use other tools while investigating. "
    + GATE_CLOSE_LINE
)

SKEPTIC_INSTRUCTIONS = (
    "You are a skeptic. You are given the prompt that was sent to the original "
    "agent and that agent's output. Investigate whether the work was accomplished. "
    "You may inspect context or use other tools while investigating. "
    "On fail, include concise findings the original agent can use to retry. "
    "On pass, stop — do not nag. "
    + SKEPTIC_CLOSE_LINE
)

_GATE_YES = frozenset({"yes", "y", "dangerous", "true", "1"})
_GATE_NO = frozenset({"no", "n", "safe", "false", "0"})
_SKEPTIC_PASS = frozenset({"pass", "yes", "y", "accomplished", "true", "ok", "done", "1"})
_SKEPTIC_FAIL = frozenset({"fail", "no", "n", "false", "incomplete", "0"})

TurnFn = Callable[[Any, str], Any]
ProgressFn = Callable[[dict[str, Any]], Any]


@dataclass
class VerdictSink:
    """Context-local capture of a classifier verdict tool call."""

    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    recorded: bool = False

    def record(self, tool_name: str, arguments: dict[str, Any]) -> None:
        self.tool_name = tool_name
        self.arguments = dict(arguments)
        self.recorded = True


_SINK: ContextVar[VerdictSink | None] = ContextVar(
    "swarm_classifier_verdict_sink",
    default=None,
)


def current_verdict_sink() -> VerdictSink | None:
    return _SINK.get()


@dataclass(frozen=True)
class ClassifierSpec:
    """Shared pattern for a yes/no-ish classifier role."""

    role: str
    tool_name: str
    close_line: str
    instructions: str
    fail_closed_kind: str  # "gate" | "skeptic" | custom


CLASSIFIER_SPECS: dict[str, ClassifierSpec] = {
    "gate": ClassifierSpec(
        role="gate",
        tool_name=GATE_VERDICT_TOOL,
        close_line=GATE_CLOSE_LINE,
        instructions=GATE_INSTRUCTIONS,
        fail_closed_kind="gate",
    ),
    "safety": ClassifierSpec(
        role="safety",
        tool_name=GATE_VERDICT_TOOL,
        close_line=GATE_CLOSE_LINE,
        instructions=GATE_INSTRUCTIONS,
        fail_closed_kind="gate",
    ),
    "skeptic": ClassifierSpec(
        role="skeptic",
        tool_name=SKEPTIC_VERDICT_TOOL,
        close_line=SKEPTIC_CLOSE_LINE,
        instructions=SKEPTIC_INSTRUCTIONS,
        fail_closed_kind="skeptic",
    ),
}


def register_classifier_role(spec: ClassifierSpec) -> ClassifierSpec:
    """Register (or replace) a classifier role so new yes/no seats share the pattern."""
    CLASSIFIER_SPECS[spec.role] = spec
    return spec


def spec_for_role(role: str) -> ClassifierSpec:
    key = str(role or "").strip().lower().replace("-", "_")
    if key in {"tool_gate", "toolgate"}:
        key = "gate"
    spec = CLASSIFIER_SPECS.get(key)
    if spec is None:
        raise ValueError(f"unknown classifier role: {role!r}")
    return spec


def nudge_budget(override: int | None = None) -> int:
    """Return the continue-nudge budget (default 3)."""
    if override is not None:
        return max(0, int(override))
    raw = os.environ.get(NUDGE_ENV)
    if raw is not None and str(raw).strip():
        try:
            return max(0, int(raw))
        except ValueError:
            logger.info("invalid %s=%r; using default %s", NUDGE_ENV, raw, DEFAULT_CLASSIFIER_NUDGES)
    return DEFAULT_CLASSIFIER_NUDGES


def continue_nudge(tool_name: str, attempt: int, max_nudges: int) -> str:
    """Short continue prompt that repeats the exact verdict tool name."""
    return (
        f"You must call `{tool_name}` to finish. "
        f"Prose alone is not a verdict. "
        f"Nudged classifier ({attempt}/{max_nudges})."
    )


def classifier_ui_label(phase: str, nudge: int = 0, max_nudges: int = DEFAULT_CLASSIFIER_NUDGES) -> str:
    """Optional UI honesty labels (Waiting / Nudged / fail-closed / accepted)."""
    if phase == "waiting":
        return "Waiting for verdict…"
    if phase == "nudged":
        return f"Nudged classifier ({nudge}/{max_nudges})"
    if phase == "fail_closed":
        return "Classifier failed closed (no verdict tool)"
    return "Verdict accepted"


def ensure_classifier_instructions(instructions: str | None, role: str) -> str:
    """Keep custom investigation text; re-append the mandatory tool-closing line."""
    spec = spec_for_role(role)
    text = str(instructions or "").strip()
    if spec.tool_name in text:
        return text or spec.instructions
    if not text:
        return spec.instructions
    return f"{text}\n\n{spec.close_line}"


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return {}
        if raw[0] in "{[":
            try:
                import json

                parsed = json.loads(raw)
            except (TypeError, ValueError):
                return {"raw": raw}
            if isinstance(parsed, dict):
                return parsed
        return {"raw": raw}
    return {"raw": value}


def _norm_token(value: Any) -> str:
    return str(value or "").strip().lower().strip(".,!?;:\"'")


def parse_gate_tool_args(
    arguments: dict[str, Any] | None = None,
    *,
    verdict: str | None = None,
    dangerous: bool | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Interpret structured ``submit_gate_verdict`` arguments only (not prose)."""
    args = dict(arguments or {})
    if verdict is None:
        verdict = args.get("verdict") or args.get("token")
    if dangerous is None and "dangerous" in args:
        dangerous = bool(args.get("dangerous"))
    if dangerous is None and "is_dangerous" in args:
        dangerous = bool(args.get("is_dangerous"))
    if not reason:
        reason = str(args.get("reason") or args.get("findings") or "")
    if dangerous is not None:
        flag = bool(dangerous)
    else:
        token = _norm_token(verdict)
        if token in _GATE_YES:
            flag = True
        elif token in _GATE_NO:
            flag = False
        else:
            raise ValueError(
                f"{GATE_VERDICT_TOOL} requires verdict=yes|no or dangerous=bool; got {verdict!r}"
            )
    label = "yes" if flag else "no"
    return {"verdict": label, "dangerous": flag, "reason": reason}


def parse_skeptic_tool_args(
    arguments: dict[str, Any] | None = None,
    *,
    verdict: str | None = None,
    accomplished: bool | None = None,
    reason: str = "",
    checks: Any = None,
) -> dict[str, Any]:
    """Interpret structured ``submit_skeptic_verdict`` arguments only (not prose)."""
    args = dict(arguments or {})
    if verdict is None:
        verdict = args.get("verdict") or args.get("token")
    if accomplished is None and "accomplished" in args:
        accomplished = bool(args.get("accomplished"))
    if accomplished is None and "pass" in args and isinstance(args.get("pass"), bool):
        accomplished = bool(args.get("pass"))
    if not reason:
        reason = str(args.get("reason") or args.get("findings") or "")
    if checks is None:
        checks = args.get("checks")
    if accomplished is not None:
        flag = bool(accomplished)
    else:
        token = _norm_token(verdict)
        if token in _SKEPTIC_PASS:
            flag = True
        elif token in _SKEPTIC_FAIL:
            flag = False
        else:
            raise ValueError(
                f"{SKEPTIC_VERDICT_TOOL} requires verdict=pass|fail; got {verdict!r}"
            )
    label = "pass" if flag else "fail"
    return {
        "verdict": label,
        "accomplished": flag,
        "reason": reason,
        "checks": checks,
    }


def submit_gate_verdict(
    verdict: str,
    reason: str = "",
    dangerous: bool | None = None,
) -> str:
    """Record the gate classification. The agent must call this to finish."""
    parsed = parse_gate_tool_args(verdict=verdict, dangerous=dangerous, reason=reason)
    sink = current_verdict_sink()
    if sink is not None:
        sink.record(GATE_VERDICT_TOOL, parsed)
    return f"Gate verdict recorded: {parsed['verdict']}"


def submit_skeptic_verdict(
    verdict: str,
    reason: str = "",
    checks: Any = None,
    accomplished: bool | None = None,
) -> str:
    """Record the skeptic classification. The agent must call this to finish."""
    parsed = parse_skeptic_tool_args(
        verdict=verdict,
        accomplished=accomplished,
        reason=reason,
        checks=checks,
    )
    sink = current_verdict_sink()
    if sink is not None:
        sink.record(SKEPTIC_VERDICT_TOOL, parsed)
    return f"Skeptic verdict recorded: {parsed['verdict']}"


def _verdict_callable(role: str) -> Callable[..., str]:
    if spec_for_role(role).fail_closed_kind == "skeptic":
        return submit_skeptic_verdict
    return submit_gate_verdict


def make_verdict_tool(role: str) -> Any:
    """openai-agents ``function_tool`` when available; otherwise the raw callable."""
    spec = spec_for_role(role)
    fn = _verdict_callable(role)
    try:
        from agents import function_tool

        return function_tool(fn, name_override=spec.tool_name)
    except TypeError:
        try:
            from agents import function_tool

            wrapped = function_tool(fn)
            if getattr(wrapped, "name", None) != spec.tool_name:
                try:
                    wrapped.name = spec.tool_name
                except Exception:
                    pass
            return wrapped
        except Exception:
            fn.name = spec.tool_name  # type: ignore[attr-defined]
            return fn
    except Exception:
        fn.name = spec.tool_name  # type: ignore[attr-defined]
        return fn


def attach_classifier_tools(agent: Any, role: str) -> Any:
    """Attach the verdict tool and re-append the mandatory close line on *agent*."""
    if agent is None:
        return agent
    spec = spec_for_role(role)
    tool = make_verdict_tool(role)
    tools = list(getattr(agent, "tools", None) or [])
    names = {getattr(item, "name", None) or getattr(item, "__name__", None) for item in tools}
    if spec.tool_name not in names:
        tools.append(tool)
        try:
            agent.tools = tools
        except Exception:
            logger.debug("could not assign classifier tools on %r", agent)
    instructions = getattr(agent, "instructions", None)
    if instructions is None and isinstance(agent, dict):
        instructions = agent.get("instructions") or agent.get("system_prompt")
    ensured = ensure_classifier_instructions(instructions, role)
    try:
        agent.instructions = ensured
    except Exception:
        if isinstance(agent, dict):
            agent["instructions"] = ensured
    return agent


def _iter_mapping_calls(payload: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    if payload.get("name") and ("arguments" in payload or "args" in payload):
        yield str(payload["name"]), _as_dict(payload.get("arguments") or payload.get("args"))
    for key in ("tool_calls", "calls", "function_calls"):
        items = payload.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                fn = item.get("function") if isinstance(item.get("function"), dict) else {}
                name = item.get("name") or fn.get("name")
                args = item.get("arguments") or item.get("args") or fn.get("arguments")
                if name:
                    yield str(name), _as_dict(args)


def _item_tool_name(item: Any) -> str | None:
    if item is None:
        return None
    if isinstance(item, dict):
        fn = item.get("function") if isinstance(item.get("function"), dict) else {}
        name = item.get("name") or item.get("tool_name") or fn.get("name")
        return str(name) if name else None
    raw = getattr(item, "raw_item", None)
    for candidate in (
        getattr(item, "name", None),
        getattr(item, "tool_name", None),
        getattr(raw, "name", None),
        getattr(getattr(raw, "function", None), "name", None),
    ):
        if candidate:
            return str(candidate)
    return None


def _item_tool_args(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        fn = item.get("function") if isinstance(item.get("function"), dict) else {}
        return _as_dict(item.get("arguments") or item.get("args") or fn.get("arguments"))
    raw = getattr(item, "raw_item", None)
    for candidate in (
        getattr(item, "arguments", None),
        getattr(item, "args", None),
        getattr(raw, "arguments", None),
        getattr(getattr(raw, "function", None), "arguments", None),
    ):
        if candidate is not None:
            return _as_dict(candidate)
    return {}


def extract_verdict_tool_call(result: Any, tool_name: str) -> dict[str, Any] | None:
    """Pull structured args for *tool_name* from a turn result. Never reads prose."""
    if result is None:
        return None
    if isinstance(result, dict):
        for name, args in _iter_mapping_calls(result):
            if name == tool_name:
                return args
        return None
    calls = getattr(result, "tool_calls", None)
    if isinstance(calls, list):
        for item in calls:
            if _item_tool_name(item) == tool_name:
                return _item_tool_args(item)
    items = getattr(result, "new_items", None)
    if isinstance(items, list):
        for item in items:
            if _item_tool_name(item) == tool_name:
                return _item_tool_args(item)
    return None


def _emit(progress_fn: ProgressFn | None, payload: dict[str, Any]) -> None:
    if progress_fn is None:
        return
    try:
        result = progress_fn(payload)
        if hasattr(result, "__await__"):
            run_coro_sync(result)
    except Exception:
        logger.debug("classifier progress emit skipped", exc_info=True)


def _call_turn(turn_fn: TurnFn, agent: Any, message: str) -> Any:
    result = turn_fn(agent, message)
    if hasattr(result, "__await__"):
        return run_coro_sync(result)
    return result


def _default_turn(agent: Any, message: str) -> Any:
    classify = getattr(agent, "classify", None)
    if callable(classify):
        return classify(message)
    respond = getattr(agent, "respond", None)
    if callable(respond):
        return respond(message)
    as_tool = getattr(agent, "as_tool", None)
    if callable(as_tool):
        try:
            tool = as_tool(
                tool_name=getattr(agent, "name", None) or "classifier",
                tool_description="Classifier role; finish via the dedicated verdict tool.",
            )
            on_invoke = getattr(tool, "on_invoke_tool", None)
            if callable(on_invoke):
                result = on_invoke(None, message)
                if hasattr(result, "__await__"):
                    result = run_coro_sync(result)
                return result
        except Exception as exc:
            logger.debug("classifier as_tool invoke skipped: %s", exc)
    try:
        from agents import Runner

        async def _run() -> Any:
            return await Runner.run(agent, message)

        return run_coro_sync(_run())
    except Exception as exc:
        logger.info("classifier Runner unavailable (%s)", exc)
        raise


def _parse_recorded(spec: ClassifierSpec, arguments: dict[str, Any]) -> dict[str, Any]:
    if spec.fail_closed_kind == "skeptic":
        return parse_skeptic_tool_args(arguments)
    return parse_gate_tool_args(arguments)


@dataclass
class ClassifierTurnResult:
    """Outcome of one classifier determination (possibly after nudges)."""

    accepted: bool
    failed_closed: bool
    payload: dict[str, Any] | None
    nudges: int
    nudge_messages: list[str] = field(default_factory=list)
    tool_name: str = ""
    role: str = ""
    phase: str = "waiting"
    error: str | None = None
    raw: str = ""

    @property
    def ui_label(self) -> str:
        return classifier_ui_label(self.phase, self.nudges, max(self.nudges, DEFAULT_CLASSIFIER_NUDGES))


def fail_closed_result(spec: ClassifierSpec, nudges: int, nudge_messages: list[str]) -> ClassifierTurnResult:
    """Honest fail-closed payload after the nudge budget is exhausted."""
    tool = spec.tool_name
    error = (
        f"FAIL_CLOSED: {tool} was not called after {nudges} continue "
        f"nudge(s). Last assistant prose was not parsed as a verdict."
    )
    if spec.fail_closed_kind == "skeptic":
        payload = {
            "verdict": "fail",
            "accomplished": False,
            "reason": error,
            "checks": None,
            "failed_closed": True,
            "needs_human": False,
        }
    else:
        payload = {
            "verdict": "yes",
            "dangerous": True,
            "reason": error,
            "failed_closed": True,
            "needs_human": True,
        }
    return ClassifierTurnResult(
        accepted=False,
        failed_closed=True,
        payload=payload,
        nudges=nudges,
        nudge_messages=list(nudge_messages),
        tool_name=tool,
        role=spec.role,
        phase="fail_closed",
        error=error,
        raw=error,
    )


def run_classifier_until_verdict(
    *,
    agent: Any,
    prompt: str,
    role: str,
    invoke_fn: TurnFn | None = None,
    max_nudges: int | None = None,
    progress_fn: ProgressFn | None = None,
) -> ClassifierTurnResult:
    """Run *agent* until the verdict tool is called, or fail closed.

    *invoke_fn* is ``(agent, message) -> turn_result``. A string return is
    treated as prose (never a verdict). A mapping / object with ``tool_calls``
    or a live :func:`submit_gate_verdict` / :func:`submit_skeptic_verdict`
    call (captured on the context sink) is accepted.
    """
    spec = spec_for_role(role)
    budget = nudge_budget(max_nudges)
    turn_fn = invoke_fn or _default_turn
    attach_classifier_tools(agent, role)
    sink = VerdictSink()
    token = _SINK.set(sink)
    nudge_messages: list[str] = []
    message = prompt
    try:
        _emit(
            progress_fn,
            {
                "phase": "waiting",
                "tool_name": spec.tool_name,
                "nudge": 0,
                "max_nudges": budget,
                "ui_label": classifier_ui_label("waiting", 0, budget),
            },
        )
        for attempt in range(budget + 1):
            try:
                result = _call_turn(turn_fn, agent, message)
            except Exception as exc:
                logger.info(
                    "classifier turn failed role=%s tool=%s attempt=%s (%s)",
                    spec.role,
                    spec.tool_name,
                    attempt,
                    exc,
                )
                result = None
            args: dict[str, Any] | None = None
            if sink.recorded and sink.tool_name == spec.tool_name:
                args = sink.arguments
            if args is None:
                args = extract_verdict_tool_call(result, spec.tool_name)
                if args is not None:
                    try:
                        args = _parse_recorded(spec, args)
                    except ValueError as exc:
                        logger.info("classifier tool args invalid (%s); treating as missing", exc)
                        args = None
            if args is not None:
                _emit(
                    progress_fn,
                    {
                        "phase": "accepted",
                        "tool_name": spec.tool_name,
                        "nudge": attempt,
                        "max_nudges": budget,
                        "ui_label": classifier_ui_label("accepted", attempt, budget),
                    },
                )
                return ClassifierTurnResult(
                    accepted=True,
                    failed_closed=False,
                    payload=args,
                    nudges=attempt,
                    nudge_messages=list(nudge_messages),
                    tool_name=spec.tool_name,
                    role=spec.role,
                    phase="accepted",
                    raw=str(args),
                )
            if attempt >= budget:
                break
            nudge = continue_nudge(spec.tool_name, attempt + 1, budget)
            nudge_messages.append(nudge)
            logger.info(
                "classifier nudge %s/%s role=%s tool=%s",
                attempt + 1,
                budget,
                spec.role,
                spec.tool_name,
            )
            _emit(
                progress_fn,
                {
                    "phase": "nudged",
                    "tool_name": spec.tool_name,
                    "nudge": attempt + 1,
                    "max_nudges": budget,
                    "ui_label": classifier_ui_label("nudged", attempt + 1, budget),
                },
            )
            message = nudge
        closed = fail_closed_result(spec, len(nudge_messages), nudge_messages)
        _emit(
            progress_fn,
            {
                "phase": "fail_closed",
                "tool_name": spec.tool_name,
                "nudge": closed.nudges,
                "max_nudges": budget,
                "ui_label": classifier_ui_label("fail_closed", closed.nudges, budget),
                "error": closed.error,
            },
        )
        return closed
    finally:
        _SINK.reset(token)
