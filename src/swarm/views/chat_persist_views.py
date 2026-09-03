"""SPA chat thread restore + Settings-only retention actions.

``GET /chat/thread/`` hydrates an agent thread after reload / agent switch.
``PATCH /chat/thread/`` edits one message on an API-agent thread (REQ-49).
Retention (archive, restore, empty trash) lives on ``/settings/`` only.
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from swarm.core import chat_store
from swarm.core.agent_kind import can_edit_agent_messages, classify_agent_kind
from swarm.models import ChatConversation, ChatMessage

logger = logging.getLogger(__name__)

_ALLOWED_ACTIONS = frozenset({"archive", "archive_all", "restore", "empty_trash"})


def _user_key(user) -> str:
    return chat_store.user_key_for(user)


def _public_messages(messages) -> list[dict]:
    out: list[dict] = []
    for item in messages or []:
        row = {
            "role": item.get("role", "user"),
            "content": item.get("content", ""),
        }
        if item.get("edited"):
            row["edited"] = True
        out.append(row)
    return out


def _thread_payload(agent: str, conversation_id: str, messages, *, agent_raw: str | None = None) -> dict:
    kind = classify_agent_kind(agent_raw or agent)
    return {
        "agent_id": agent,
        "conversation_id": conversation_id,
        "kind": kind,
        "editable": kind == "api",
        "messages": _public_messages(messages),
    }


def _messages_from_db(user, conversation_id: str) -> list[dict]:
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


def _load_thread_messages(user, agent: str, conversation_id: str) -> tuple[list[dict], str]:
    """JSON store first, then Django rows, then the live WS cache."""
    user_key = _user_key(user)
    record = chat_store.load(user_key, agent)
    messages = (record or {}).get("messages") if record else None
    resolved_id = conversation_id
    if record and record.get("conversation_id"):
        resolved_id = record["conversation_id"]
    if not messages:
        db_id = (record or {}).get("conversation_id") or conversation_id
        messages = _messages_from_db(user, db_id)
        if messages and record is None:
            try:
                chat_store.save(
                    user_key,
                    agent,
                    messages,
                    conversation_id=db_id,
                )
            except OSError:
                logger.exception("Failed to backfill chat JSON for %s/%s", user_key, agent)
        resolved_id = db_id or resolved_id
    if not messages:
        from swarm.consumers import IN_MEMORY_CONVERSATIONS, _conversation_cache_key

        for cid in (conversation_id, resolved_id):
            if not cid:
                continue
            cached = IN_MEMORY_CONVERSATIONS.get(_conversation_cache_key(user, cid))
            if cached:
                messages = list(cached)
                resolved_id = cid
                break
    return list(messages or []), resolved_id


def _sync_django_and_memory(user, messages, conversation_ids: list[str]) -> None:
    """Mirror the edited transcript onto Django rows + the live WS cache."""
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
        IN_MEMORY_CONVERSATIONS[_conversation_cache_key(user, cid)] = [
            {"role": item.get("role", "user"), "content": item.get("content", "")}
            for item in messages
        ]


@login_required
@require_http_methods(["GET", "PATCH"])
def chat_thread(request):
    """Hydrate (GET) or edit (PATCH) the persisted transcript for one agent."""
    agent_raw = request.GET.get("agent")
    agent = chat_store.normalize_agent_id(agent_raw)
    user_key = _user_key(request.user)
    conversation_id = chat_store.conversation_id_for(request.user, agent)
    messages, conversation_id = _load_thread_messages(request.user, agent, conversation_id)

    if request.method == "GET":
        return JsonResponse(_thread_payload(agent, conversation_id, messages, agent_raw=agent_raw))

    # PATCH — API-agent threads only (CLI/remote are owned outside swarm).
    if not can_edit_agent_messages(agent_raw or agent):
        return JsonResponse(
            {"error": "Edits are only allowed on API-agent threads."},
            status=403,
        )
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    index = body.get("index")
    content = body.get("content")
    if type(index) is not int:
        return JsonResponse({"error": "index must be an integer."}, status=400)
    if not isinstance(content, str):
        return JsonResponse({"error": "content must be a string."}, status=400)
    if index < 0 or index >= len(messages):
        return JsonResponse({"error": "No message at that index."}, status=404)

    current = dict(messages[index])
    current["content"] = content
    current["edited"] = True
    messages[index] = current

    client_cid = body.get("conversation_id")
    if isinstance(client_cid, str) and client_cid.strip():
        conversation_id = client_cid.strip()

    try:
        chat_store.save(
            user_key,
            agent,
            messages,
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
        messages,
        [conversation_id, chat_store.conversation_id_for(request.user, agent)],
    )
    return JsonResponse(_thread_payload(agent, conversation_id, messages, agent_raw=agent_raw))


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
