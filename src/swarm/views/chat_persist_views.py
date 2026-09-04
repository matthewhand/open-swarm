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
    return [
        {"role": row.sender, "content": row.content}
        for row in chat.chat_messages.all()
    ]


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
        out.append(row)
    return out


def _sync_django_and_memory(user, messages, conversation_ids: list[str]) -> None:
    from swarm.consumers import IN_MEMORY_CONVERSATIONS, _conversation_cache_key

    seen: set[str] = set()
    for cid in conversation_ids:
        if not cid or cid in seen:
            continue
        seen.add(cid)
        chat, created = ChatConversation.objects.get_or_create(
            conversation_id=cid,
            defaults={"student": user},
        )
        if not created and chat.student_id is not None and chat.student_id != user.pk:
            continue
        if chat.student_id is None:
            chat.student = user
            chat.save(update_fields=["student"])
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
            if item.get("edited"):
                row["edited"] = True
            mem_rows.append(row)
        IN_MEMORY_CONVERSATIONS[_conversation_cache_key(user, cid)] = mem_rows


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
    conversation_id = chat_store.conversation_id_for(request.user, agent)
    requested_cid = (request.GET.get("conversation_id") or "").strip()
    if request.method in ("PATCH", "POST"):
        body = _json_body(request)
        if isinstance(body.get("conversation_id"), str) and body["conversation_id"].strip():
            requested_cid = body["conversation_id"].strip()
    fresh_task = is_new_chat_per_task(agent)
    if fresh_task:
        record = chat_store.load(
            user_key,
            agent,
            conversation_id=requested_cid,
            session_id=requested_cid,
        ) if requested_cid else None
    else:
        record = chat_store.load(user_key, agent)
    messages = (record or {}).get("messages") if record else None
    if fresh_task and not requested_cid:
        # New task: do not hydrate the reused agent transcript.
        messages = []
    if not messages and not (fresh_task and not requested_cid):
        db_id = requested_cid or (record or {}).get("conversation_id") or conversation_id
        messages = _messages_from_db(request.user, db_id)
        if messages and record is None and not fresh_task:
            # Upgrade path: mirror an existing Django row onto disk.
            try:
                chat_store.save(
                    user_key,
                    agent,
                    messages,
                    conversation_id=db_id,
                )
            except OSError:
                logger.exception("Failed to backfill chat JSON for %s/%s", user_key, agent)
    if requested_cid:
        conversation_id = requested_cid
    elif record and record.get("conversation_id") and not fresh_task:
        conversation_id = record["conversation_id"]
    conversation_id, summaries = _summaries_for(
        requested_cid,
        (record or {}).get("conversation_id") if record else "",
        conversation_id,
    )
    if not conversation_id:
        conversation_id = requested_cid or (record or {}).get("conversation_id") or chat_store.conversation_id_for(
            request.user, agent
        )
    sessions = list_active_task_sessions(user_key, agent) if fresh_task else []
    kind = classify_agent_kind(agent_raw or agent)
    payload = {
        "agent_id": agent,
        "conversation_id": conversation_id,
        "kind": kind,
        "editable": kind == "api",
        "new_chat_per_task": fresh_task,
        "active_sessions": sessions,
        "messages": _public_messages(messages),
        "summaries": summaries if not (fresh_task and not requested_cid) else [],
    }
    if request.method == "GET":
        return JsonResponse(payload)

    if request.method == "POST":
        body = _json_body(request)
        msg = body.get("message")
        if isinstance(msg, dict) and msg.get("content"):
            current_messages = list(messages or [])
            new_row = {
                "role": str(msg.get("role") or "status"),
                "content": str(msg.get("content") or ""),
            }
            current_messages.append(new_row)
            try:
                chat_store.save(
                    user_key,
                    agent,
                    current_messages,
                    conversation_id=conversation_id,
                )
            except OSError:
                logger.exception("Failed to append chat JSON for %s/%s", user_key, agent)
            _sync_django_and_memory(
                request.user,
                current_messages,
                [conversation_id, chat_store.conversation_id_for(request.user, agent)],
            )
            payload["messages"] = _public_messages(current_messages)
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
    current_messages = list(messages or [])
    if index < 0 or index >= len(current_messages):
        return JsonResponse({"error": "No message at that index."}, status=404)
    updated = dict(current_messages[index])
    updated["content"] = content
    updated["edited"] = True
    current_messages[index] = updated
    try:
        chat_store.save(
            user_key,
            agent,
            current_messages,
            conversation_id=conversation_id,
        )
    except OSError:
        logger.exception("Failed to persist edited chat JSON for %s/%s", user_key, agent)
        return JsonResponse(
            {"error": "Could not persist the edit. See server logs."},
            status=500,
        )
    _sync_django_and_memory(
        request.user,
        current_messages,
        [conversation_id, chat_store.conversation_id_for(request.user, agent)],
    )
    payload["messages"] = _public_messages(current_messages)
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
