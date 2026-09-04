"""Socratic configure flow for Support — tools/prompts of OTHER agents."""

from __future__ import annotations

import re
from typing import Any

from swarm.core.decision_question import format_decision_question
from swarm.core.support_context import agent_role, live_context

_INTENT_RE = re.compile(
    r"\b(configure|config|tools?|prompts?|instructions?|mcp)\b",
    re.IGNORECASE,
)

_FALLBACK_AGENTS = ["hybrid_team", "skeptic", "gate"]


def wants_configure(user_text: str) -> bool:
    return bool(_INTENT_RE.search(user_text or ""))


def other_agent_choices(context: dict[str, Any] | None = None) -> list[str]:
    ctx = context or live_context()
    names: list[str] = []
    seen: set[str] = set()
    for agent in ctx.get("agents") or []:
        if agent_role(agent) == "support":
            continue
        label = str(agent.get("name") or agent.get("id") or "").strip()
        ident = str(agent.get("id") or "").strip()
        key = label.lower()
        if not label or key in seen:
            continue
        seen.add(key)
        if ident:
            seen.add(ident.lower())
        names.append(label)
        if len(names) >= 6:
            break
    return names or list(_FALLBACK_AGENTS)


def _named_agent(user_text: str, choices: list[str]) -> str:
    lowered = (user_text or "").lower()
    for name in choices:
        if name.lower() in lowered:
            return name
    for token in _FALLBACK_AGENTS:
        if token in lowered:
            return token
    return ""


def socratic_configure_question(
    user_text: str,
    context: dict[str, Any] | None = None,
) -> str:
    """One laconic question card. Never a config dump."""
    ctx = context or live_context()
    choices = other_agent_choices(ctx)
    target = _named_agent(user_text, choices)
    lowered = (user_text or "").lower()
    wants_tools = bool(re.search(r"\b(tools?|mcp)\b", lowered))
    wants_prompt = bool(re.search(r"\b(prompts?|instructions?)\b", lowered))

    if target and wants_tools:
        return format_decision_question(
            ask=f"{target} tools — add which?",
            choices=["Files", "Web", "Shell", "None"],
            other="Name a tool",
            question_id="configure-tools",
        )
    if target and wants_prompt:
        return format_decision_question(
            ask=f"{target} prompt — tone?",
            choices=["Laconic", "Thorough", "Keep current"],
            other="Describe the prompt",
            question_id="configure-prompt",
        )
    if target:
        return format_decision_question(
            ask=f"{target} — tools or prompt?",
            choices=["Tools", "Prompt"],
            other="Something else",
            question_id="configure-facet",
        )
    return format_decision_question(
        ask="Configure which agent?",
        choices=choices,
        other="Name an agent",
        question_id="configure-agent",
    )
