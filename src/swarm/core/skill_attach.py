"""Attach discovered SKILL.md skills to API / Blueprint chat turns.

CLI (``cli_agent``) and Support apply skills themselves. Today's stored ``api``
seats are Blueprint-backed (ADR-006); this helper prepends requested skills to
the last user message before those recipes run.

True inference-only API seats (ADR-006 Phase 2) do not exist on ``main`` yet —
skill attach stays on Blueprint-backed seats until that path lands.
"""

from __future__ import annotations

from typing import Any

# Blueprints that already call apply_skill_to_prompt internally.
SELF_APPLYING_SKILL_BLUEPRINTS = frozenset({"cli_agent", "cli_fusion", "support"})


def blueprint_applies_own_skills(blueprint_id: str | None) -> bool:
    return str(blueprint_id or "").strip().lower() in SELF_APPLYING_SKILL_BLUEPRINTS


def apply_skills_to_messages(
    messages: list[dict[str, Any]] | None,
    params: dict[str, Any] | None,
    workdir: str | None = None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Apply ``skill`` / ``skills`` params to the last user message.

    Returns ``(messages, applied_names, missing_names)``. Unknown names are
    reported and skipped — the turn still runs.
    """
    from swarm.blueprints.common.cli_fusion_support import apply_skills_to_prompt
    from swarm.core.skills import requested_skill_names

    msgs = list(messages or [])
    if not requested_skill_names(params):
        return msgs, [], []
    for index in range(len(msgs) - 1, -1, -1):
        row = msgs[index]
        if not isinstance(row, dict) or row.get("role") != "user":
            continue
        content = row.get("content")
        text = content if isinstance(content, str) else str(content or "")
        new_text, applied, missing = apply_skills_to_prompt(text, params, workdir=workdir)
        next_row = dict(row)
        next_row["content"] = new_text
        out = msgs[:]
        out[index] = next_row
        return out, applied, missing
    from swarm.core.skills import resolve_skills

    _found, missing = resolve_skills(params)
    return msgs, [], missing
