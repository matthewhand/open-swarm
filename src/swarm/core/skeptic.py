"""Skeptic role: review whether the original agent accomplished the prompt.

When a ``skeptic`` is wired onto a team:

* After the original agent runs, the skeptic sees the **same prompt** that was
  sent plus the agent's output.
* If the work was **not** accomplished, findings are handed back to the
  original agent (openai-agents as-tool / retry loop) for another attempt.
* Retries are bounded (default 2). Never an infinite loop.
* If accomplished, **stop**. Do not nag the user.

When no skeptic is wired, the original agent runs once.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from swarm.core.agent_roles import (
    ROLE_SKEPTIC,
    attach_role,
    find_role_agent,
    normalize_agent_role,
)
from swarm.core.async_utils import run_coro_sync

logger = logging.getLogger(__name__)

SKEPTIC_ROLE = ROLE_SKEPTIC
SKEPTIC_MAX_RETRIES = 2

SKEPTIC_INSTRUCTIONS = (
    "You are a skeptic. You are given the prompt that was sent to the original "
    "agent and that agent's output. Investigate whether the work was accomplished. "
    "First line: a single token YES if accomplished, NO if not. "
    "If NO, follow with concise findings the original agent can use to retry. "
    "If YES, stop. Do not nag, do not add extra critique."
)

_YES = frozenset({"YES", "Y", "ACCOMPLISHED", "TRUE", "DONE", "1"})
_NO = frozenset({"NO", "N", "FALSE", "INCOMPLETE", "FAIL", "0"})

RunFn = Callable[[Any, str], Any]
ReviewFn = Callable[[Any, str, str], Any]


@dataclass
class SkepticVerdict:
    accomplished: bool
    findings: str = ""
    raw: str = ""


@dataclass
class SkepticRunResult:
    output: str
    attempts: int
    retries: int
    accomplished: bool | None
    findings: list[str] = field(default_factory=list)
    nagged: bool = False


def parse_skeptic_verdict(text: Any) -> SkepticVerdict:
    """Parse YES/NO (first token) plus optional findings."""
    if isinstance(text, bool):
        return SkepticVerdict(accomplished=text, raw=str(text))
    if isinstance(text, dict):
        accomplished = bool(
            text.get("accomplished", text.get("yes", text.get("ok", False)))
        )
        findings = str(text.get("findings") or text.get("reason") or "")
        return SkepticVerdict(accomplished=accomplished, findings=findings, raw=str(text))
    raw = str(text or "").strip()
    if not raw:
        return SkepticVerdict(accomplished=False, findings="empty skeptic reply", raw=raw)
    lines = raw.splitlines() or [""]
    first = (lines[0] if lines else "").strip()
    parts = first.split()
    if not parts:
        return SkepticVerdict(accomplished=False, findings=raw, raw=raw)
    token = parts[0].upper().strip(".,!?;:\"'")
    rest = "\n".join(lines[1:]).strip()
    if token in _YES:
        return SkepticVerdict(accomplished=True, findings="", raw=raw)
    if token in _NO:
        return SkepticVerdict(
            accomplished=False,
            findings=rest or raw,
            raw=raw,
        )
    # Prose without a token: treat as not accomplished so findings can retry.
    return SkepticVerdict(accomplished=False, findings=raw, raw=raw)


def _review_prompt(original_prompt: str, output: str) -> str:
    return (
        "Original prompt sent to the agent:\n"
        f"{original_prompt}\n\n"
        "Agent output:\n"
        f"{output}\n\n"
        "Was the work accomplished? First line YES or NO only. "
        "If NO, add findings for a retry."
    )


def _handoff_retry_prompt(original_prompt: str, findings: str, attempt: int) -> str:
    return (
        f"{original_prompt}\n\n"
        "---\n"
        f"Skeptic findings (retry {attempt}/{SKEPTIC_MAX_RETRIES}): the previous "
        "attempt did not accomplish the work. Address these findings and try again:\n"
        f"{findings}\n"
    )


def _stringify_output(result: Any) -> str:
    if result is None:
        return ""
    final = getattr(result, "final_output", None)
    if final is not None:
        return str(final)
    return str(result)


def _invoke_skeptic(
    skeptic: Any,
    original_prompt: str,
    output: str,
    *,
    review_fn: ReviewFn | None = None,
    invoke_fn: Callable[[Any, str], Any] | None = None,
) -> SkepticVerdict:
    if review_fn is not None:
        return parse_skeptic_verdict(review_fn(skeptic, original_prompt, output))
    prompt = _review_prompt(original_prompt, output)
    if invoke_fn is not None:
        return parse_skeptic_verdict(invoke_fn(skeptic, prompt))
    review = getattr(skeptic, "review", None)
    if callable(review):
        return parse_skeptic_verdict(review(original_prompt, output))
    respond = getattr(skeptic, "respond", None)
    if callable(respond):
        return parse_skeptic_verdict(respond(prompt))
    as_tool = getattr(skeptic, "as_tool", None)
    if callable(as_tool):
        try:
            tool = as_tool(
                tool_name=getattr(skeptic, "name", None) or "skeptic",
                tool_description="Review whether the original agent accomplished the work.",
            )
            on_invoke = getattr(tool, "on_invoke_tool", None)
            if callable(on_invoke):
                result = on_invoke(None, prompt)
                if hasattr(result, "__await__"):
                    result = run_coro_sync(result)
                return parse_skeptic_verdict(result)
        except Exception as exc:
            logger.debug("skeptic as_tool invoke skipped: %s", exc)
    try:
        from agents import Runner

        async def _run() -> str:
            result = await Runner.run(skeptic, prompt, max_turns=1)
            return _stringify_output(result)

        return parse_skeptic_verdict(run_coro_sync(_run()))
    except Exception as exc:
        logger.info("skeptic Runner unavailable (%s)", exc)
        raise


async def _call_run_fn(run_fn: RunFn, agent: Any, prompt: str) -> Any:
    result = run_fn(agent, prompt)
    if isinstance(result, Awaitable):
        return await result
    return result


async def run_with_skeptic(
    *,
    agent: Any,
    prompt: str,
    skeptic: Any = None,
    max_retries: int = SKEPTIC_MAX_RETRIES,
    run_fn: RunFn | None = None,
    review_fn: ReviewFn | None = None,
    invoke_fn: Callable[[Any, str], Any] | None = None,
) -> SkepticRunResult:
    """Run *agent* on *prompt*; optionally loop through a wired skeptic.

    Bounded retries: the original agent is invoked at most ``1 + max_retries``
    times. ``max_retries`` defaults to 2.
    """
    if run_fn is None:
        async def _default_run(current_agent: Any, message: str) -> str:
            from agents import Runner

            result = await Runner.run(current_agent, message)
            return _stringify_output(result)

        run_fn = _default_run  # type: ignore[assignment]

    first = await _call_run_fn(run_fn, agent, prompt)
    output = _stringify_output(first)
    if skeptic is None and review_fn is None:
        return SkepticRunResult(
            output=output,
            attempts=1,
            retries=0,
            accomplished=None,
            nagged=False,
        )

    bound = max(0, int(max_retries))
    findings_log: list[str] = []
    attempts = 1
    current = output
    for retry_i in range(bound):
        verdict = _invoke_skeptic(
            skeptic,
            prompt,
            current,
            review_fn=review_fn,
            invoke_fn=invoke_fn,
        )
        if verdict.accomplished:
            return SkepticRunResult(
                output=current,
                attempts=attempts,
                retries=retry_i,
                accomplished=True,
                findings=findings_log,
                nagged=False,
            )
        findings_log.append(verdict.findings or verdict.raw)
        retry_prompt = _handoff_retry_prompt(prompt, verdict.findings or verdict.raw, retry_i + 1)
        nxt = await _call_run_fn(run_fn, agent, retry_prompt)
        current = _stringify_output(nxt)
        attempts += 1

    # Exhausted retries. One last review is optional — do not nag the user
    # with extra skeptic commentary beyond the findings already applied.
    last = _invoke_skeptic(
        skeptic,
        prompt,
        current,
        review_fn=review_fn,
        invoke_fn=invoke_fn,
    )
    if last.accomplished:
        return SkepticRunResult(
            output=current,
            attempts=attempts,
            retries=bound,
            accomplished=True,
            findings=findings_log,
            nagged=False,
        )
    if last.findings:
        findings_log.append(last.findings)
    return SkepticRunResult(
        output=current,
        attempts=attempts,
        retries=bound,
        accomplished=False,
        findings=findings_log,
        nagged=False,
    )


def attach_skeptic_as_tool(coordinator: Any, skeptic: Any) -> Any:
    """Relate skeptic output to the coordinator via openai-agents ``as_tool``."""
    if coordinator is None or skeptic is None:
        return coordinator
    attach_role(skeptic, ROLE_SKEPTIC)
    as_tool = getattr(skeptic, "as_tool", None)
    if not callable(as_tool):
        return coordinator
    try:
        tool = as_tool(
            tool_name=getattr(skeptic, "name", None) or "skeptic",
            tool_description=(
                "Review whether the original prompt was accomplished. "
                "Returns YES or NO plus findings."
            ),
        )
        tools = list(getattr(coordinator, "tools", None) or [])
        tools.append(tool)
        coordinator.tools = tools
    except Exception as exc:
        logger.debug("skeptic as_tool wiring skipped: %s", exc)
    return coordinator


def skeptic_from_team(agents: Any) -> Any | None:
    """Return the wired skeptic agent, or ``None`` (no retry loop)."""
    return find_role_agent(agents, ROLE_SKEPTIC)


def is_skeptic_role(role: Any) -> bool:
    return normalize_agent_role(role) == ROLE_SKEPTIC
