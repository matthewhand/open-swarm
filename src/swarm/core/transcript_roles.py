"""Transcript roles that are UI chrome vs model context (REQ-70 / #407).

Info/status lines persist for the human (with timestamps) and must never
enter the LLM payload. Compact summaries and speaker labelling operate on
the filtered list only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

# Bubble-less chrome. ``system`` is kept: compact summaries and real prompts
# use it. Frontend maps leftover ``system`` rows to status *display* only.
# ``prior_history`` is the REQ-104 archive pill — same family as status/info.
UI_ONLY_ROLES = frozenset({"status", "info"})
UI_ONLY_KINDS = frozenset({"prior_history"})
MODEL_ROLES = frozenset({"system", "user", "assistant", "tool", "developer"})


def _role_of(item: dict[str, Any]) -> str:
    return str(item.get("role") or item.get("sender") or "user").strip().lower()


def is_ui_only_role(role: Any) -> bool:
    return str(role or "").strip().lower() in UI_ONLY_ROLES


def is_ui_only_item(item: Any) -> bool:
    """True for status/info rows and the prior-history archive pill."""
    if not isinstance(item, dict):
        return False
    if is_ui_only_role(_role_of(item)):
        return True
    for key in ("kind", "source_kind"):
        val = item.get(key)
        if isinstance(val, str) and val.strip().lower() in UI_ONLY_KINDS:
            return True
    return False


def message_timestamp(item: dict[str, Any] | None) -> str:
    """ISO timestamp already on the row, or empty."""
    if not isinstance(item, dict):
        return ""
    ts = item.get("ts") or item.get("timestamp") or item.get("created_at")
    return ts.strip() if isinstance(ts, str) and ts.strip() else ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp_ui_event(item: dict[str, Any]) -> dict[str, Any]:
    """Ensure a UI-only row has ``ts`` so reload can show when it occurred."""
    row = dict(item)
    if not message_timestamp(row):
        row["ts"] = utc_now_iso()
    return row


def messages_for_model(messages: Iterable[Any] | None) -> list[dict[str, Any]]:
    """Transcript → LLM payload: drop status/info and prior_history archive.

    Keeps real turns + tool rows. Preserves ``name`` / ``tool_call_id`` /
    ``tool_calls`` so speaker identity and tool pairing survive. Does not
    invent content or wrap speakers.
    """
    out: list[dict[str, Any]] = []
    for raw in messages or []:
        if not isinstance(raw, dict):
            continue
        role = _role_of(raw)
        if is_ui_only_item(raw):
            continue
        if role not in MODEL_ROLES:
            # Unknown chrome (e.g. leftover ``suggestions``) stays out of context.
            continue
        content = raw.get("content")
        if content is None:
            content = raw.get("text") or ""
        row: dict[str, Any] = {"role": role, "content": content}
        name = raw.get("name") or raw.get("speaker") or raw.get("agent")
        if isinstance(name, str) and name.strip():
            row["name"] = name.strip()
        if raw.get("tool_call_id"):
            row["tool_call_id"] = raw["tool_call_id"]
        if raw.get("tool_calls"):
            row["tool_calls"] = raw["tool_calls"]
        out.append(row)
    return out


def context_blob(messages: Iterable[dict[str, Any]] | None) -> str:
    """Concatenated payload text for leak assertions."""
    parts: list[str] = []
    for item in messages or []:
        parts.append(str(item.get("role") or ""))
        parts.append(str(item.get("content") or ""))
        parts.append(str(item.get("name") or ""))
    return "\n".join(parts)
