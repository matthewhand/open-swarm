"""REQ-71: structured GitHub PR-opened tool events (no markdown scrape).

A tool result becomes a ``pr_opened`` chrome event only when it already
carries a GitHub pull URL and/or explicit ``type: pr_opened``. Optional
branch / ``+N/-M`` / file counts are copied when present and never invented.
"""

from __future__ import annotations

import json
import re
from typing import Any

PR_OPENED_TYPE = "pr_opened"

# https://github.com/{owner}/{repo}/pull/{n} — no LAN, no :8001, no other hosts.
_GITHUB_PR_URL = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/\d+(?:/[A-Za-z0-9._~-]*)?(?:\?[^#]*)?(?:#.*)?$",
    re.IGNORECASE,
)

_URL_KEYS = ("url", "html_url", "pr_url", "pull_request_url")
_TITLE_KEYS = ("title", "name")
_NUMBER_KEYS = ("number", "pr_number", "pull_number")
_BRANCH_KEYS = ("branch", "head_ref", "head")
_ADDITIONS_KEYS = ("additions", "additions_count", "plus")
_DELETIONS_KEYS = ("deletions", "deletions_count", "minus")
_FILES_KEYS = ("files_changed", "changed_files", "files")
_STATUS_KEYS = ("status", "state")


def is_github_pr_url(value: object) -> bool:
    """True only for a public ``https://github.com/…/pull/N`` URL."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text or "://" not in text:
        return False
    lowered = text.lower()
    if lowered.startswith(("http://", "ws://", "wss://")):
        return False
    if "localhost" in lowered or "127.0.0.1" in lowered:
        return False
    if ":8001" in lowered:
        return False
    return bool(_GITHUB_PR_URL.match(text))


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("+-").isdigit():
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _first_str(obj: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        raw = obj.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _first_int(obj: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        parsed = _as_int(obj.get(key))
        if parsed is not None:
            return parsed
    return None


def _github_pr_url_from(obj: dict[str, Any]) -> str | None:
    for key in _URL_KEYS:
        raw = obj.get(key)
        if is_github_pr_url(raw):
            return str(raw).strip()
    return None


def _opener_from(obj: dict[str, Any], *, agent_id: str = "", conversation_id: str = "") -> dict[str, str]:
    raw = obj.get("opener")
    opener: dict[str, str] = {}
    if isinstance(raw, dict):
        oid = raw.get("agent_id") or raw.get("agentId") or raw.get("id")
        name = raw.get("name")
        cid = raw.get("conversation_id") or raw.get("conversationId")
        if isinstance(oid, str) and oid.strip():
            opener["agent_id"] = oid.strip()
        if isinstance(name, str) and name.strip():
            opener["name"] = name.strip()
        if isinstance(cid, str) and cid.strip():
            opener["conversation_id"] = cid.strip()
    if agent_id and "agent_id" not in opener:
        opener["agent_id"] = agent_id
    if conversation_id and "conversation_id" not in opener:
        opener["conversation_id"] = conversation_id
    return opener


def _unwrap_candidate(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        for nested_key in ("pull_request", "pr", "result", "data"):
            nested = value.get(nested_key)
            if isinstance(nested, dict) and (
                _github_pr_url_from(nested) or nested.get("type") == PR_OPENED_TYPE
            ):
                return nested
        return value
    return None


def parse_pr_opened(
    value: Any,
    *,
    agent_id: str = "",
    conversation_id: str = "",
) -> dict[str, Any] | None:
    """Return a chrome payload, or None when this is not a PR-opened result."""
    if isinstance(value, str):
        text = value.strip()
        if not text.startswith("{"):
            return None
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
    obj = _unwrap_candidate(value)
    if obj is None:
        return None

    explicit = str(obj.get("type") or "").strip() == PR_OPENED_TYPE
    url = _github_pr_url_from(obj)
    number = _first_int(obj, _NUMBER_KEYS)
    title = _first_str(obj, _TITLE_KEYS)
    if not explicit and not url:
        return None
    if not explicit and url and number is None and title is None:
        # A lone GitHub link is not enough — require number or title.
        return None

    payload: dict[str, Any] = {"type": PR_OPENED_TYPE}
    if url:
        payload["url"] = url
    if number is not None:
        payload["number"] = number
    if title:
        payload["title"] = title

    branch = obj.get("branch")
    if not isinstance(branch, str) or not branch.strip():
        head = obj.get("head")
        if isinstance(head, dict):
            ref = head.get("ref")
            if isinstance(ref, str) and ref.strip():
                branch = ref
        elif isinstance(head, str) and head.strip() and "/" not in head.strip():
            branch = head
        else:
            branch = _first_str(obj, ("head_ref",))
    if isinstance(branch, str) and branch.strip():
        payload["branch"] = branch.strip()

    additions = _first_int(obj, _ADDITIONS_KEYS)
    if additions is not None:
        payload["additions"] = additions
    deletions = _first_int(obj, _DELETIONS_KEYS)
    if deletions is not None:
        payload["deletions"] = deletions
    files_changed = _first_int(obj, _FILES_KEYS)
    if files_changed is not None:
        payload["files_changed"] = files_changed

    status = _first_str(obj, _STATUS_KEYS)
    if status and status.lower() not in {PR_OPENED_TYPE, "tool_status", "tool_approval"}:
        payload["status"] = status

    opener = _opener_from(obj, agent_id=agent_id, conversation_id=conversation_id)
    if opener:
        payload["opener"] = opener
    return payload


def persist_pr_opened_message(messages: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    """Append a status row so reload can rehydrate the card (not model context)."""
    content = json.dumps(payload, separators=(",", ":"))
    for row in messages:
        if row.get("role") == "status" and row.get("content") == content:
            return
    from swarm.core.transcript_roles import stamp_event

    messages.append(stamp_event({"role": "status", "kind": "status", "content": content}))
