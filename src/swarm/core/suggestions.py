"""REQ-85: ``suggestions`` role — short quick-select prompts after a turn.

A *consumer* agent with **Use suggestions** on invokes a ``suggestions``-role
specialist (openai-agents ``as_tool`` / handoff) and the chat UI renders the
returned strings as chips. Chips are chrome: they are never appended to the
transcript and never sent as extra LLM context (#407).

Fail-soft: a bad, empty, or failed list is an honest omission — no crash,
no toast dump.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

from swarm.core.agent_roles import (
    ROLE_SUGGESTIONS,
    attach_role,
    find_role_agent,
    normalize_agent_role,
)
from swarm.core.async_utils import run_coro_sync

logger = logging.getLogger(__name__)

SUGGESTIONS_ROLE = ROLE_SUGGESTIONS
MIN_SUGGESTIONS = 1
MAX_SUGGESTIONS = 5
MAX_CHIP_CHARS = 80

SUGGESTIONS_INSTRUCTIONS = (
    "You prepare short quick-select prompts for the operator. "
    "Return a JSON object with a single key 'suggestions' whose value is "
    "a list of 2-5 concise strings the user might send next. "
    "No numbering, no quotes in the strings, no explanation."
)

KICKSTART_CANNED = (
    "What should we explore first?",
    "Show me how this agent is set up",
    "Give me a short status",
)

CONTINUE_CANNED = (
    "Can you expand on that?",
    "What are the main risks or trade-offs?",
    "What would a minimal next step look like?",
)

SuggestFn = Callable[[str, str], Any]


def parse_suggestions(raw: Any) -> list[str]:
    """Normalize a suggestions payload into 1–5 short unique strings.

    Accepts a list, a ``{"suggestions": [...]}`` dict, a JSON string, or
    newline-separated text. Anything unusable becomes ``[]``.
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = list(raw)
    elif isinstance(raw, dict):
        items = raw.get("suggestions")
        if items is None:
            items = raw.get("prompts") or raw.get("chips") or raw.get("options")
        if not isinstance(items, (list, tuple)):
            return []
        items = list(items)
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            items = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
        else:
            return parse_suggestions(parsed)
    else:
        return []

    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item is None:
            continue
        chip = str(item).strip()
        if not chip:
            continue
        chip = " ".join(chip.split())
        if len(chip) > MAX_CHIP_CHARS:
            chip = chip[: MAX_CHIP_CHARS - 1].rstrip() + "…"
        key = chip.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(chip)
        if len(out) >= MAX_SUGGESTIONS:
            break
    return out if len(out) >= MIN_SUGGESTIONS else []


def canned_kickstart() -> list[str]:
    return list(KICKSTART_CANNED)


def canned_continue(messages: list[dict[str, Any]] | None = None) -> list[str]:
    last_user = ""
    if messages:
        for row in reversed(messages):
            if isinstance(row, dict) and row.get("role") == "user":
                last_user = str(row.get("content") or "").strip()
                break
    if last_user:
        snippet = last_user[:48].rstrip()
        extra = f"Go deeper on: {snippet}" if snippet else ""
        chips = list(CONTINUE_CANNED)
        if extra:
            chips = [extra, *chips[:2]]
        return parse_suggestions(chips)
    return list(CONTINUE_CANNED)


def _stringify_output(result: Any) -> Any:
    if result is None:
        return ""
    final = getattr(result, "final_output", None)
    if final is not None:
        return final
    return result


def _invoke_suggestions(
    agent: Any,
    prompt: str,
    *,
    suggest_fn: SuggestFn | None = None,
) -> list[str]:
    if suggest_fn is not None:
        return parse_suggestions(suggest_fn(agent, prompt))
    suggest = getattr(agent, "suggest", None)
    if callable(suggest):
        return parse_suggestions(suggest(prompt))
    respond = getattr(agent, "respond", None)
    if callable(respond):
        return parse_suggestions(respond(prompt))
    as_tool = getattr(agent, "as_tool", None)
    if callable(as_tool):
        try:
            tool = as_tool(
                tool_name=getattr(agent, "name", None) or "suggestions",
                tool_description="Prepare 2-5 short quick-select prompts.",
            )
            on_invoke = getattr(tool, "on_invoke_tool", None)
            if callable(on_invoke):
                result = on_invoke(None, prompt)
                if hasattr(result, "__await__"):
                    result = run_coro_sync(result)
                return parse_suggestions(result)
        except Exception as exc:
            logger.debug("suggestions as_tool invoke skipped: %s", exc)
    try:
        from agents import Runner

        async def _run() -> Any:
            result = await Runner.run(agent, prompt, max_turns=1)
            return _stringify_output(result)

        return parse_suggestions(run_coro_sync(_run()))
    except Exception as exc:
        logger.info("suggestions Runner unavailable (%s)", exc)
        return []


def _mode_prompt(mode: str, messages: list[dict[str, Any]] | None) -> str:
    if mode == "kickstart":
        return (
            "The thread is empty. Suggest 2-5 short first messages the operator "
            "might send to start usefully. Return JSON {\"suggestions\": [...]}."
        )
    last_user = ""
    last_assistant = ""
    if messages:
        for row in reversed(messages):
            if not isinstance(row, dict):
                continue
            role = row.get("role")
            content = str(row.get("content") or "").strip()
            if role == "assistant" and not last_assistant:
                last_assistant = content
            elif role == "user" and not last_user:
                last_user = content
            if last_user and last_assistant:
                break
    return (
        "Suggest 2-5 short follow-up messages the operator might send next.\n\n"
        f"Last user message:\n{last_user or '(none)'}\n\n"
        f"Last assistant output:\n{last_assistant or '(none)'}\n\n"
        "Return JSON {\"suggestions\": [...]}."
    )


def run_suggestions(
    *,
    mode: str = "kickstart",
    messages: list[dict[str, Any]] | None = None,
    agents: Any = None,
    suggest_fn: SuggestFn | None = None,
) -> list[str]:
    """Return chips for kickstart or continue. Empty list on any failure."""
    kind = "kickstart" if str(mode).strip().lower() != "continue" else "continue"
    try:
        if suggest_fn is not None:
            agent = find_role_agent(agents, ROLE_SUGGESTIONS) if agents else None
            return _invoke_suggestions(agent, _mode_prompt(kind, messages), suggest_fn=suggest_fn)
        if os.environ.get("SWARM_TEST_MODE"):
            return canned_kickstart() if kind == "kickstart" else canned_continue(messages)
        agent = find_role_agent(agents, ROLE_SUGGESTIONS) if agents else None
        if agent is None:
            return []
        return _invoke_suggestions(agent, _mode_prompt(kind, messages))
    except Exception:
        logger.debug("suggestions run omitted", exc_info=True)
        return []


def suggestions_payload_for_turn(
    agent_id: str | None,
    messages: list[dict[str, Any]] | None = None,
    *,
    agents: Any = None,
) -> dict[str, Any] | None:
    """WS/API payload after a finished turn, or ``None`` when chips should hide."""
    from swarm.core.agent_settings import is_use_suggestions

    if not is_use_suggestions(agent_id):
        return None
    has_assistant = any(
        isinstance(row, dict) and row.get("role") == "assistant"
        for row in (messages or [])
    )
    chips = run_suggestions(
        mode="continue" if has_assistant else "kickstart",
        messages=messages,
        agents=agents,
    )
    if not chips:
        return None
    return {"type": "suggestions", "suggestions": chips}


def attach_suggestions_as_tool(coordinator: Any, suggestions: Any) -> Any:
    """Expose the suggestions specialist on the coordinator via ``as_tool``."""
    if coordinator is None or suggestions is None:
        return coordinator
    attach_role(suggestions, ROLE_SUGGESTIONS)
    as_tool = getattr(suggestions, "as_tool", None)
    if not callable(as_tool):
        return coordinator
    try:
        tool = as_tool(
            tool_name=getattr(suggestions, "name", None) or "suggestions",
            tool_description="Prepare 2-5 short quick-select prompts for the operator.",
        )
        tools = list(getattr(coordinator, "tools", None) or [])
        tools.append(tool)
        coordinator.tools = tools
    except Exception as exc:
        logger.debug("suggestions as_tool wiring skipped: %s", exc)
    return coordinator


def suggestions_from_team(agents: Any) -> Any | None:
    return find_role_agent(agents, ROLE_SUGGESTIONS)


def is_suggestions_role(role: Any) -> bool:
    return normalize_agent_role(role) == ROLE_SUGGESTIONS
