"""User-answerable decision questions (Socratic cards).

Any agent can emit a fenced ``question`` block. The chat UI renders it as a
card: multiple-choice options plus a last open-string field. Distinct from
one-way System pills (config intel; not answerable).
"""

from __future__ import annotations

import json
import re
from typing import Any

QUESTION_FENCE = "question"

_FENCE_RE = re.compile(
    r"```question\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def format_decision_question(
    *,
    ask: str,
    choices: list[str],
    other: str = "Other",
    question_id: str = "q",
) -> str:
    """Laconic ```question fence any agent can emit."""
    cleaned = [str(item).strip() for item in choices if str(item).strip()]
    if not ask.strip() or not cleaned:
        raise ValueError("ask and at least one choice are required")
    payload = {
        "id": str(question_id or "q").strip() or "q",
        "ask": ask.strip(),
        "choices": cleaned,
        "other": (other or "Other").strip() or "Other",
    }
    return f"```{QUESTION_FENCE}\n{json.dumps(payload, ensure_ascii=False)}\n```"


def parse_decision_question(text: str) -> dict[str, Any] | None:
    """Return {id, ask, choices, other} or None when the fence is missing/invalid."""
    if not text:
        return None
    match = _FENCE_RE.search(text)
    if not match:
        return None
    try:
        raw = json.loads(match.group(1))
    except (TypeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    ask = str(raw.get("ask") or "").strip()
    choices_raw = raw.get("choices")
    if not ask or not isinstance(choices_raw, list):
        return None
    choices = [str(item).strip() for item in choices_raw if str(item).strip()]
    if not choices:
        return None
    return {
        "id": str(raw.get("id") or "q").strip() or "q",
        "ask": ask,
        "choices": choices,
        "other": str(raw.get("other") or "Other").strip() or "Other",
    }


def strip_decision_question(text: str) -> str:
    """Prose around the fence (usually empty — keep cards laconic)."""
    if not text:
        return ""
    return _FENCE_RE.sub("", text).strip()
