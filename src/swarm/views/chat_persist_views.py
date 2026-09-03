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

from swarm.core import chat_store
from swarm.core.chat_compact import (
    CompactError,
    compact_backlog,
    list_summaries,
    summary_to_dict,
)
from swarm.models import ChatConversation

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


@login_required
@ensure_csrf_cookie
@require_http_methods(["GET"])
def chat_thread(request):
    """Return the persisted transcript for one agent (JSON store, DB fallback)."""
    agent = chat_store.normalize_agent_id(request.GET.get("agent"))
    user_key = _user_key(request.user)
    conversation_id = chat_store.conversation_id_for(request.user, agent)
    requested_cid = (request.GET.get("conversation_id") or "").strip()
    record = chat_store.load(user_key, agent)
    messages = (record or {}).get("messages") if record else None
    if not messages:
        db_id = requested_cid or (record or {}).get("conversation_id") or conversation_id
        messages = _messages_from_db(request.user, db_id)
        if messages and record is None:
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
    elif record and record.get("conversation_id"):
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
    return JsonResponse(
        {
            "agent_id": agent,
            "conversation_id": conversation_id,
            "messages": [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in (messages or [])
            ],
            "summaries": summaries,
        }
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
