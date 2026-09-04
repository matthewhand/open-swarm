"""REQ-65 session policy: reuse one chat, or mint a new one per task.

Default (off) keeps today's behaviour: one conversation per ``(user, agent)``.
When ``new_chat_per_task`` is on:

* each user task / CoS handoff / ``as_tool`` invocation gets an empty session
* several such sessions may run concurrently for the same agent definition
* API agents: swarm creates the session (do not continue ``previous_response_id``)
* CLI / remote: do **not** resume a stored session id (#369 still applies when off)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from swarm.core.agent_settings import (
    is_new_chat_per_task,
    stored_cli_session_id,
    stored_remote_session_id,
)
from swarm.core.chat_store import conversation_id_for, normalize_agent_id, user_key_for

# In-process registry of concurrent task sessions (also mirrored on disk).
_ACTIVE: dict[tuple[str, str], list[str]] = {}


@dataclass(frozen=True)
class TaskSession:
    """One allocated chat session for an agent task."""

    agent_id: str
    conversation_id: str
    new_chat_per_task: bool
    empty: bool
    resume_external: bool
    task_id: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


def should_resume_external_session(agent_id: str | None) -> bool:
    """CLI/remote resume (#369). False when new-chat-per-task is on."""
    if not (agent_id or "").strip():
        return True
    return not is_new_chat_per_task(agent_id)


def resume_cli_session_id(agent_id: str | None, stored: str | None = None) -> str | None:
    """Session id to pass to a CLI ``--resume`` flag, or None to start fresh.

    When the agent is in new-chat-per-task mode this always returns ``None``
    even if a stored id exists — do not fake a restored transcript.
    """
    if not should_resume_external_session(agent_id):
        return None
    if stored:
        text = str(stored).strip()
        return text or None
    if not (agent_id or "").strip():
        return None
    return stored_cli_session_id(agent_id)


def resume_remote_session_id(agent_id: str | None, stored: str | None = None) -> str | None:
    """Remote thread/session id to reuse, or None for a new remote job."""
    if not should_resume_external_session(agent_id):
        return None
    if stored:
        text = str(stored).strip()
        return text or None
    if not (agent_id or "").strip():
        return None
    return stored_remote_session_id(agent_id)


def mint_task_conversation_id(
    user=None,
    agent_id: str = "",
    task_id: str | None = None,
) -> str:
    """Mint a unique conversation id for one on-mode task."""
    agent = normalize_agent_id(agent_id)
    suffix = (task_id or "").strip() or uuid.uuid4().hex
    suffix = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in suffix)[:64]
    pk = getattr(user, "pk", None)
    if pk is None:
        pk = getattr(user, "id", None)
    prefix = f"task-{pk}-" if pk is not None else "task-"
    return f"{prefix}{agent}-{suffix}"[:128]


def register_active_session(user_key: str, agent_id: str, conversation_id: str) -> None:
    """Remember a running task session so the rail can show a count."""
    key = (str(user_key), normalize_agent_id(agent_id))
    cid = (conversation_id or "").strip()
    if not cid:
        return
    bucket = _ACTIVE.setdefault(key, [])
    if cid not in bucket:
        bucket.append(cid)


def list_active_task_sessions(user_key: str, agent_id: str) -> list[str]:
    """In-process concurrent session ids for one agent (plus disk, if any)."""
    key = (str(user_key), normalize_agent_id(agent_id))
    memory = list(_ACTIVE.get(key) or [])
    try:
        from swarm.core import chat_store

        disk = [
            row.get("conversation_id") or ""
            for row in chat_store.list_sessions(user_key, agent_id)
            if row.get("conversation_id")
        ]
    except Exception:
        disk = []
    seen: list[str] = []
    for cid in memory + disk:
        if cid and cid not in seen:
            seen.append(cid)
    return seen


def clear_active_sessions() -> None:
    """Test helper."""
    _ACTIVE.clear()


def allocate_task_session(
    user,
    agent_id: str,
    *,
    task_id: str | None = None,
    new_chat_per_task: bool | None = None,
) -> TaskSession:
    """Pick the conversation id for one user task / CoS handoff / as_tool call.

    Off: deterministic ``conversation_id_for(user, agent)`` (reuse).
    On: mint a unique empty session and register it as concurrent.
    """
    agent = normalize_agent_id(agent_id)
    on = is_new_chat_per_task(agent) if new_chat_per_task is None else bool(new_chat_per_task)
    if not on:
        cid = conversation_id_for(user, agent)
        return TaskSession(
            agent_id=agent,
            conversation_id=cid,
            new_chat_per_task=False,
            empty=False,
            resume_external=True,
            task_id=task_id or "",
        )
    cid = mint_task_conversation_id(user, agent, task_id)
    try:
        uk = user_key_for(user)
    except Exception:
        uk = "u0"
    register_active_session(uk, agent, cid)
    return TaskSession(
        agent_id=agent,
        conversation_id=cid,
        new_chat_per_task=True,
        empty=True,
        resume_external=False,
        task_id=task_id or "",
    )


def messages_for_task(
    agent_id: str,
    messages: list[dict[str, Any]] | None,
    *,
    new_task: bool = True,
) -> list[dict[str, Any]]:
    """Transcript to feed a worker. On-mode new tasks start empty."""
    if new_task and is_new_chat_per_task(agent_id):
        return []
    return list(messages or [])


def continue_api_previous_response(agent_id: str, previous_response_id: str | None) -> str | None:
    """API agents: swarm owns session create.

    On-mode workers never continue ``previous_response_id`` — each invocation
    is a new ``resp_*`` with an empty prior transcript.
    """
    if not previous_response_id:
        return None
    if is_new_chat_per_task(agent_id):
        return None
    return str(previous_response_id)
