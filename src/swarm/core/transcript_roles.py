"""REQ-70: chrome is side-channel metadata; the UI reconstructs it.

Status / info / hop lines are **not** model turns. They live in ``ui_events``
(with timestamps). The UI rebuilds transcript chrome from that metadata.
Model context is built from real user / assistant / tool turns only.

If a mixed ``messages`` list still exists (schema 1, in-flight WS, Django
mirror), exclude-of-status is a **safety belt** — not the product story.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

# Stored as ``ui_events[].kind`` (and accepted as a leftover ``role``).
CHROME_KINDS = frozenset({"status", "info", "hop"})
# Model-context chrome. ``system`` is a real model role (compact summaries,
# CLI flatten). Leftover thread ``system`` rows are still stored as events.
CHROME_ROLES = frozenset({"status", "info", "hop"})
MODEL_ROLES = frozenset({"user", "assistant", "tool", "developer", "system"})


def _role_of(item: dict[str, Any]) -> str:
    return str(item.get("role") or item.get("sender") or item.get("kind") or "user").strip().lower()


def is_chrome_item(item: Any) -> bool:
    """True for status/info/hop chrome — never a model turn."""
    if not isinstance(item, dict):
        return False
    kind = str(item.get("kind") or "").strip().lower()
    if kind in CHROME_KINDS:
        return True
    return _role_of(item) in CHROME_ROLES


def is_thread_chrome(item: Any) -> bool:
    """Thread-store chrome, including leftover ``system`` display rows."""
    if is_chrome_item(item):
        return True
    return isinstance(item, dict) and _role_of(item) == "system"


def is_model_turn(item: Any) -> bool:
    if not isinstance(item, dict) or is_chrome_item(item):
        return False
    role = _role_of(item)
    if role in MODEL_ROLES:
        return True
    # Unknown leftover chrome (suggestions, …) stays out of the model.
    return False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def message_timestamp(item: dict[str, Any] | None) -> str:
    if not isinstance(item, dict):
        return ""
    ts = item.get("ts") or item.get("timestamp") or item.get("created_at")
    return ts.strip() if isinstance(ts, str) and ts.strip() else ""


def stamp_event(item: dict[str, Any]) -> dict[str, Any]:
    """Ensure a chrome event has ``ts`` so reload can show when it occurred."""
    row = dict(item)
    if not message_timestamp(row):
        row["ts"] = utc_now_iso()
    return row


def _copy_turn(item: dict[str, Any], *, seq: int | None = None) -> dict[str, Any]:
    role = _role_of(item)
    if role not in MODEL_ROLES:
        role = "user"
    content = item.get("content")
    if content is None:
        content = item.get("text") or ""
    row: dict[str, Any] = {"role": role, "content": content if isinstance(content, str) else str(content)}
    ts = message_timestamp(item)
    if ts:
        row["ts"] = ts
    if item.get("edited") is True or item.get("edited") == "true":
        row["edited"] = True
    name = item.get("name") or item.get("speaker") or item.get("agent")
    if isinstance(name, str) and name.strip():
        row["name"] = name.strip()
    if item.get("tool_call_id"):
        row["tool_call_id"] = item["tool_call_id"]
    if item.get("tool_calls"):
        row["tool_calls"] = item["tool_calls"]
    use_seq = item.get("seq") if isinstance(item.get("seq"), int) else seq
    if isinstance(use_seq, int):
        row["seq"] = use_seq
    return row


def _copy_event(item: dict[str, Any], *, seq: int | None = None) -> dict[str, Any]:
    kind = str(item.get("kind") or _role_of(item) or "status").strip().lower()
    if kind == "system":
        kind = "info"
    if kind not in CHROME_KINDS:
        kind = "status"
    content = item.get("content")
    if content is None:
        content = item.get("text") or ""
    row = stamp_event(
        {
            "kind": kind,
            "role": kind if kind in CHROME_ROLES else "status",
            "content": content if isinstance(content, str) else str(content),
        }
    )
    ts = message_timestamp(item)
    if ts:
        row["ts"] = ts
    use_seq = item.get("seq") if isinstance(item.get("seq"), int) else seq
    if isinstance(use_seq, int):
        row["seq"] = use_seq
    return row


def _event_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("kind") or item.get("role") or "status"),
        str(item.get("content") or ""),
        message_timestamp(item),
    )


def _merge_events(primary: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {_event_key(row) for row in primary}
    out = list(primary)
    for row in extra:
        key = _event_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def split_store(
    messages: Iterable[Any] | None,
    ui_events: Iterable[Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate a (possibly mixed) list into model turns + chrome events.

    Mixed schema-1 ``messages`` are migrated here: chrome rows become events
    and keep their original index as ``seq`` so the UI can reconstruct order.
    """
    turns: list[dict[str, Any]] = []
    extracted: list[dict[str, Any]] = []
    for index, raw in enumerate(messages or []):
        if not isinstance(raw, dict):
            continue
        if is_thread_chrome(raw):
            extracted.append(_copy_event(raw, seq=index))
            continue
        if is_model_turn(raw) or _role_of(raw) in MODEL_ROLES:
            turns.append(_copy_turn(raw, seq=index))
    events = [_copy_event(item, seq=item.get("seq") if isinstance(item, dict) else None) for item in (ui_events or []) if isinstance(item, dict)]
    if extracted:
        events = extracted if not events else _merge_events(events, extracted)
    return turns, events


def next_seq(turns: Iterable[dict[str, Any]], events: Iterable[dict[str, Any]]) -> int:
    values = [0]
    for row in list(turns or []) + list(events or []):
        seq = row.get("seq")
        if isinstance(seq, int):
            values.append(seq)
    return max(values) + 1


def append_turn(
    turns: list[dict[str, Any]],
    events: list[dict[str, Any]],
    item: dict[str, Any],
) -> dict[str, Any]:
    """Append a model turn (never chrome). Returns the stored turn."""
    row = _copy_turn(item, seq=next_seq(turns, events))
    if not message_timestamp(row):
        row["ts"] = utc_now_iso()
    turns.append(row)
    return row


def append_event(
    turns: list[dict[str, Any]],
    events: list[dict[str, Any]],
    item: dict[str, Any],
) -> dict[str, Any]:
    """Append chrome to the side channel (never into model turns)."""
    row = _copy_event(item, seq=next_seq(turns, events))
    events.append(row)
    return row


def reconstruct_display(
    turns: Iterable[dict[str, Any]] | None,
    ui_events: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """UI timeline: interleave turns + chrome by ``seq`` (then ``ts``).

    Chrome rows are emitted as ``role=status`` (or ``info``/``hop``) so the
    existing centred-chrome renderer can paint them. This is reconstruction,
    not a mixed store.
    """
    tagged: list[tuple[int, int, str, dict[str, Any]]] = []
    for index, turn in enumerate(turns or []):
        if not isinstance(turn, dict):
            continue
        seq = turn.get("seq") if isinstance(turn.get("seq"), int) else index
        tagged.append((int(seq), index, "turn", turn))
    offset = len(tagged)
    for index, event in enumerate(ui_events or []):
        if not isinstance(event, dict):
            continue
        seq = event.get("seq") if isinstance(event.get("seq"), int) else (10**6 + index)
        tagged.append((int(seq), offset + index, "event", event))
    tagged.sort(key=lambda row: (row[0], row[1]))
    out: list[dict[str, Any]] = []
    for _seq, _idx, kind, item in tagged:
        if kind == "turn":
            row = _copy_turn(item)
            if isinstance(item.get("seq"), int):
                row["seq"] = item["seq"]
            out.append(row)
            continue
        event = _copy_event(item)
        display = {
            "role": event.get("role") or event.get("kind") or "status",
            "content": event.get("content") or "",
            "kind": event.get("kind") or "status",
        }
        if event.get("ts"):
            display["ts"] = event["ts"]
        if isinstance(event.get("seq"), int):
            display["seq"] = event["seq"]
        out.append(display)
    return out


def turns_for_model(messages: Iterable[Any] | None) -> list[dict[str, Any]]:
    """Safety belt: model payload from turns; drop leftover chrome if mixed."""
    out: list[dict[str, Any]] = []
    for raw in messages or []:
        if not isinstance(raw, dict):
            continue
        if is_chrome_item(raw):
            continue
        role = _role_of(raw)
        if role not in MODEL_ROLES:
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
        parts.append(str(item.get("kind") or ""))
        parts.append(str(item.get("content") or ""))
        parts.append(str(item.get("name") or ""))
    return "\n".join(parts)


def chrome_already_has_notice(
    turns: Iterable[dict[str, Any]] | None,
    events: Iterable[dict[str, Any]] | None,
    text: str,
) -> bool:
    """True when this turn already recorded the same chrome line."""
    needle = (text or "").strip()
    if not needle:
        return False
    last_user_seq = -1
    for turn in turns or []:
        if (turn.get("role") or "") == "user":
            seq = turn.get("seq") if isinstance(turn.get("seq"), int) else last_user_seq + 1
            last_user_seq = int(seq)
    for event in events or []:
        if str(event.get("content") or "").strip() != needle:
            continue
        seq = event.get("seq") if isinstance(event.get("seq"), int) else last_user_seq + 1
        if int(seq) > last_user_seq:
            return True
    return False
