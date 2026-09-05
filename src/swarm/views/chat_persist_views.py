"""SPA chat thread restore + Settings-only retention actions.

``GET /chat/thread/`` hydrates an agent thread after reload / agent switch.
``POST /chat/compact/`` summarises a span (REQ-37). Retention (archive,
restore, empty trash) lives on ``/settings/`` only.
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from swarm.core import chat_attachments, chat_store
from swarm.core.agent_kind import can_edit_agent_messages, classify_agent_kind
from swarm.core.chat_compact import (
    CompactError,
    compact_backlog,
    list_summaries,
    summary_to_dict,
)
from swarm.models import ChatAttachment, ChatConversation, ChatMessage

logger = logging.getLogger(__name__)

_ALLOWED_ACTIONS = frozenset({"archive", "archive_all", "restore", "empty_trash"})


def _user_key(user) -> str:
    return chat_store.user_key_for(user)


def _messages_from_db(user, conversation_id: str) -> list[dict[str, str]]:
    if not conversation_id:
        return []
    try:
        chat = ChatConversation.objects.get(
            conversation_id=conversation_id,
            student=user,
        )
    except ChatConversation.DoesNotExist:
        return []
    out: list[dict[str, str]] = []
    for row in chat.chat_messages.all():
        item = {"role": row.sender, "content": row.content}
        ts = row.timestamp.isoformat() if getattr(row, "timestamp", None) else ""
        if ts:
            item["ts"] = ts
        out.append(item)
    return out


def _json_body(request) -> dict:
    content_type = request.content_type or ""
    if "application/json" in content_type:
        try:
            payload = json.loads(request.body.decode() or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}


def _summaries_for(*conversation_ids: str) -> tuple[str, list[dict]]:
    """Return ``(conversation_id, summaries)`` for the first id that has rows."""
    seen: list[str] = []
    for cid in conversation_ids:
        text = (cid or "").strip()
        if not text or text in seen:
            continue
        seen.append(text)
        rows = [summary_to_dict(row) for row in list_summaries(text)]
        if rows:
            return text, rows
    return (seen[0] if seen else ""), []


def _public_messages(messages) -> list[dict]:
    out: list[dict] = []
    for item in messages or []:
        row = {
            "role": item.get("role", "user"),
            "content": item.get("content", ""),
        }
        ts = item.get("ts") or item.get("timestamp")
        if isinstance(ts, str) and ts:
            row["ts"] = ts
        if item.get("edited"):
            row["edited"] = True
        kind = item.get("kind")
        if isinstance(kind, str) and kind:
            row["kind"] = kind
        from_cid = item.get("from_conversation_id")
        if isinstance(from_cid, str) and from_cid:
            row["from_conversation_id"] = from_cid
        seq = item.get("seq")
        if isinstance(seq, int) and not isinstance(seq, bool):
            row["seq"] = seq
        out.append(row)
    return out


def _thread_channels(record, db_messages=None) -> tuple[list[dict], list[dict]]:
    """Model turns + UI events. Schema-1 mixed rows are split."""
    from swarm.core.transcript_roles import split_store

    if record is not None:
        return split_store(record.get("messages") or [], record.get("ui_events") or [])
    return split_store(db_messages or [], [])


def _thread_payload_messages(turns, events) -> list[dict]:
    from swarm.core.transcript_roles import reconstruct_display

    return _public_messages(reconstruct_display(turns, events))


def _sync_django_and_memory(
    user, messages, conversation_ids: list[str], *, agent_id: str = ""
) -> None:
    from swarm.consumers import IN_MEMORY_CONVERSATIONS, _conversation_cache_key
    from swarm.core.agent_sessions import get_or_create_session, touch_session

    seen: set[str] = set()
    for cid in conversation_ids:
        if not cid or cid in seen:
            continue
        seen.add(cid)
        try:
            chat = get_or_create_session(user, cid, agent_id=agent_id)
        except PermissionError:
            continue
        ChatMessage.objects.filter(conversation=chat).delete()
        ChatMessage.objects.bulk_create(
            [
                ChatMessage(
                    conversation=chat,
                    sender=item.get("role", "user"),
                    content=item.get("content", ""),
                )
                for item in messages
            ]
        )
        mem_rows: list[dict] = []
        for item in messages:
            row = {
                "role": item.get("role", "user"),
                "content": item.get("content", ""),
            }
            ts = item.get("ts") or item.get("timestamp")
            if isinstance(ts, str) and ts:
                row["ts"] = ts
            if item.get("edited"):
                row["edited"] = True
            mem_rows.append(row)
        IN_MEMORY_CONVERSATIONS[_conversation_cache_key(user, cid)] = mem_rows
        try:
            touch_session(chat, messages, agent_id=agent_id)
        except Exception:
            logger.exception("Failed to touch Django session %s", cid)


@login_required
@ensure_csrf_cookie
@require_http_methods(["GET", "POST", "PATCH"])
def chat_thread(request):
    """Hydrate (GET), append (POST), or edit (PATCH) the persisted transcript for one agent."""
    from swarm.core.agent_settings import is_new_chat_per_task
    from swarm.core.session_policy import list_active_task_sessions

    agent_raw = request.GET.get("agent")
    agent = chat_store.normalize_agent_id(agent_raw)
    user_key = _user_key(request.user)
    default_cid = chat_store.conversation_id_for(request.user, agent)
    conversation_id = default_cid
    requested_cid = (request.GET.get("conversation_id") or "").strip()
    if request.method in ("PATCH", "POST"):
        body = _json_body(request)
        if isinstance(body.get("conversation_id"), str) and body["conversation_id"].strip():
            requested_cid = body["conversation_id"].strip()
    fresh_task = is_new_chat_per_task(agent)
    session_id = ""
    if requested_cid and requested_cid != default_cid:
        session_id = requested_cid
    turns: list[dict] = []
    events: list[dict] = []
    if fresh_task and not requested_cid:
        # New task: do not hydrate the reused agent transcript.
        record = None
    else:
        record = chat_store.load(
            user_key,
            agent,
            conversation_id=requested_cid,
            session_id=session_id,
        )
        db_id = requested_cid or (record or {}).get("conversation_id") or default_cid
        db_messages = [] if record and record.get("messages") else _messages_from_db(
            request.user, db_id
        )
        turns, events = _thread_channels(record, db_messages)
        if not record and turns and not session_id:
            # Upgrade path: mirror an existing Django row onto disk.
            try:
                chat_store.save(
                    user_key,
                    agent,
                    turns,
                    conversation_id=db_id,
                    ui_events=events,
                )
            except OSError:
                logger.exception("Failed to backfill chat JSON for %s/%s", user_key, agent)
    if requested_cid:
        conversation_id = requested_cid
    elif record and record.get("conversation_id") and not fresh_task:
        conversation_id = record["conversation_id"]
    # REQ-105: never fall back to another conversation's compact tree.
    if requested_cid:
        summaries = [summary_to_dict(row) for row in list_summaries(requested_cid)]
    else:
        conversation_id, summaries = _summaries_for(
            (record or {}).get("conversation_id") if record else "",
            conversation_id,
        )
    if not conversation_id:
        conversation_id = requested_cid or (record or {}).get("conversation_id") or default_cid
    sessions = list_active_task_sessions(user_key, agent) if fresh_task else []
    kind = classify_agent_kind(agent_raw or agent)
    session_title = ""
    try:
        from swarm.core.agent_sessions import get_or_create_session

        row = get_or_create_session(request.user, conversation_id, agent_id=agent)
        session_title = row.title or ""
    except Exception:
        session_title = ""
    payload = {
        "agent_id": agent,
        "conversation_id": conversation_id,
        "session_title": session_title,
        "kind": kind,
        "editable": kind == "api",
        "new_chat_per_task": fresh_task,
        "active_sessions": sessions,
        "messages": _thread_payload_messages(turns, events),
        "turns": _public_messages(turns),
        "ui_events": _public_messages(events),
        "summaries": summaries if not (fresh_task and not requested_cid) else [],
    }
    if request.method == "GET":
        return JsonResponse(payload)

    if request.method == "POST":
        body = _json_body(request)
        msg = body.get("message")
        if isinstance(msg, dict) and msg.get("content"):
            from swarm.core.transcript_roles import (
                append_event,
                append_turn,
                is_chrome_message,
                stamp_ui_event,
            )

            current_turns = list(turns)
            current_events = list(events)
            new_row = {
                "role": str(msg.get("role") or "status"),
                "content": str(msg.get("content") or ""),
            }
            ts = msg.get("ts") or msg.get("timestamp") or msg.get("created_at")
            if isinstance(ts, str) and ts.strip():
                new_row["ts"] = ts.strip()
            if is_chrome_message(new_row):
                if not new_row.get("ts"):
                    new_row = stamp_ui_event(new_row)
                append_event(
                    current_turns,
                    current_events,
                    new_row["role"],
                    new_row["content"],
                    ts=new_row.get("ts"),
                    kind=msg.get("kind"),
                )
            else:
                append_turn(
                    current_turns,
                    current_events,
                    new_row["role"],
                    new_row["content"],
                    ts=new_row.get("ts"),
                )
            try:
                chat_store.save(
                    user_key,
                    agent,
                    current_turns,
                    conversation_id=conversation_id,
                    session_id=conversation_id if conversation_id != default_cid else "",
                    ui_events=current_events,
                )
            except OSError:
                logger.exception("Failed to append chat JSON for %s/%s", user_key, agent)
            _sync_django_and_memory(
                request.user,
                current_turns,
                [conversation_id],
                agent_id=agent,
            )
            payload["messages"] = _thread_payload_messages(current_turns, current_events)
            payload["turns"] = _public_messages(current_turns)
            payload["ui_events"] = _public_messages(current_events)
            return JsonResponse(payload)
        return JsonResponse({"error": "message must be provided."}, status=400)

    if not can_edit_agent_messages(agent_raw or agent):
        return JsonResponse(
            {"error": "Edits are only allowed on API-agent threads."},
            status=403,
        )
    body = _json_body(request)
    index = body.get("index")
    content = body.get("content")
    if type(index) is not int:
        return JsonResponse({"error": "index must be an integer."}, status=400)
    if not isinstance(content, str):
        return JsonResponse({"error": "content must be a string."}, status=400)
    current_turns = list(turns)
    if index < 0 or index >= len(current_turns):
        return JsonResponse({"error": "No message at that index."}, status=404)
    updated = dict(current_turns[index])
    updated["content"] = content
    updated["edited"] = True
    current_turns[index] = updated
    try:
        chat_store.save(
            user_key,
            agent,
            current_turns,
            conversation_id=conversation_id,
            session_id=conversation_id if conversation_id != default_cid else "",
            ui_events=events,
        )
    except OSError:
        logger.exception("Failed to persist edited chat JSON for %s/%s", user_key, agent)
        return JsonResponse(
            {"error": "Could not persist the edit. See server logs."},
            status=500,
        )
    _sync_django_and_memory(
        request.user,
        current_turns,
        [conversation_id],
        agent_id=agent,
    )
    payload["messages"] = _thread_payload_messages(current_turns, events)
    payload["turns"] = _public_messages(current_turns)
    payload["ui_events"] = _public_messages(events)
    return JsonResponse(payload)


@require_http_methods(["POST"])
def chat_attachment_upload(request):
    """Store one composer file and return its id (REQ-38).

    Session cookie required (same gate as the chat websocket). Bytes go to
    the local attachment store; sqlite holds metadata. Multipart field
    ``file``; optional ``conversation_id``.
    """
    if not getattr(request.user, "is_authenticated", False):
        return JsonResponse({"error": "authentication required"}, status=401)

    uploaded = request.FILES.get("file")
    if uploaded is None:
        return JsonResponse({"error": "file is required"}, status=400)

    size = int(getattr(uploaded, "size", 0) or 0)
    if size <= 0:
        return JsonResponse({"error": "empty file"}, status=400)
    if size > chat_attachments.MAX_ATTACHMENT_BYTES:
        return JsonResponse(
            {
                "error": (
                    f"file too large (max {chat_attachments.MAX_ATTACHMENT_BYTES} bytes)"
                ),
            },
            status=413,
        )

    name = chat_attachments.safe_display_name(getattr(uploaded, "name", "") or "file")
    content_type = (getattr(uploaded, "content_type", None) or "").strip()[:255]
    conversation_id = (request.POST.get("conversation_id") or "").strip()[:255]
    data = uploaded.read()
    if len(data) > chat_attachments.MAX_ATTACHMENT_BYTES:
        return JsonResponse(
            {
                "error": (
                    f"file too large (max {chat_attachments.MAX_ATTACHMENT_BYTES} bytes)"
                ),
            },
            status=413,
        )

    row = ChatAttachment.objects.create(
        owner=request.user,
        conversation_id=conversation_id,
        original_name=name,
        content_type=content_type,
        size=len(data),
    )
    try:
        chat_attachments.write_bytes(request.user, row.id, data)
    except OSError:
        logger.exception("Failed to store chat attachment %s", row.id)
        row.delete()
        return JsonResponse({"error": "could not store file"}, status=500)

    return JsonResponse(
        {
            "id": str(row.id),
            "name": row.original_name,
            "size": row.size,
            "content_type": row.content_type,
        },
        status=201,
    )


@login_required
@require_http_methods(["POST"])
def chat_compact(request):
    """Summarise the current backlog (or a selected span) into a nested summary."""
    payload = _json_body(request)
    agent = chat_store.normalize_agent_id(
        payload.get("agent") or payload.get("agent_id") or request.POST.get("agent_id")
    )
    conversation_id = (
        (payload.get("conversation_id") or request.POST.get("conversation_id") or "")
        .strip()
    )
    if not conversation_id:
        conversation_id = chat_store.conversation_id_for(request.user, agent)
    messages = payload.get("messages")
    span_start = payload.get("span_start", payload.get("start"))
    span_end = payload.get("span_end", payload.get("end"))
    try:
        start = int(span_start) if span_start is not None and span_start != "" else None
        end = int(span_end) if span_end is not None and span_end != "" else None
    except (TypeError, ValueError):
        return JsonResponse({"error": "span_start / span_end must be integers."}, status=400)
    try:
        row, raw = compact_backlog(
            user=request.user,
            conversation_id=conversation_id,
            agent_id=agent,
            messages=messages if isinstance(messages, list) else None,
            span_start=start,
            span_end=end,
        )
    except CompactError as exc:
        return JsonResponse({"error": str(exc)}, status=exc.status)
    summaries = [summary_to_dict(item) for item in list_summaries(conversation_id)]
    from swarm.core.chat_compact import build_model_context

    return JsonResponse(
        {
            "summary": summary_to_dict(row),
            "summaries": summaries,
            "context": build_model_context(raw, list_summaries(conversation_id)),
            "raw_count": len(raw),
        }
    )


@login_required
@require_http_methods(["POST"])
def chat_retention_action(request):
    """Archive / restore / empty-trash for the signed-in user's JSON threads."""
    action = (request.POST.get("action") or "").strip()
    if action not in _ALLOWED_ACTIONS:
        return JsonResponse({"success": False, "error": "Unknown action."}, status=400)

    user_key = _user_key(request.user)
    agent = chat_store.normalize_agent_id(request.POST.get("agent_id"))

    try:
        if action == "archive":
            path = chat_store.archive(user_key, agent)
            if path is None:
                return JsonResponse(
                    {"success": False, "error": "No active chat to archive."},
                    status=404,
                )
            return JsonResponse({"success": True, "archived": agent})
        if action == "archive_all":
            archived = chat_store.archive_all(user_key)
            return JsonResponse({"success": True, "archived": archived})
        if action == "restore":
            path = chat_store.restore(user_key, agent)
            if path is None:
                return JsonResponse(
                    {"success": False, "error": "No trashed chat to restore."},
                    status=404,
                )
            return JsonResponse({"success": True, "restored": agent})
        removed = chat_store.empty_trash(user_key)
        return JsonResponse({"success": True, "removed": removed})
    except OSError:
        logger.exception("Chat retention action %s failed", action)
        return JsonResponse(
            {"success": False, "error": "Could not update chat files. See server logs."},
            status=500,
        )
