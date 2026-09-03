"""SPA chat thread restore + Settings-only retention actions.

``GET /chat/thread/`` hydrates an agent thread after reload / agent switch.
Retention (archive, restore, empty trash) lives on ``/settings/`` only.
"""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from swarm.core import chat_store
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


@login_required
@require_http_methods(["GET"])
def chat_thread(request):
    """Return the persisted transcript for one agent (JSON store, DB fallback)."""
    agent = chat_store.normalize_agent_id(request.GET.get("agent"))
    user_key = _user_key(request.user)
    conversation_id = chat_store.conversation_id_for(request.user, agent)
    record = chat_store.load(user_key, agent)
    messages = (record or {}).get("messages") if record else None
    if not messages:
        db_id = (record or {}).get("conversation_id") or conversation_id
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
    if record and record.get("conversation_id"):
        conversation_id = record["conversation_id"]
    return JsonResponse(
        {
            "agent_id": agent,
            "conversation_id": conversation_id,
            "messages": [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in (messages or [])
            ],
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
