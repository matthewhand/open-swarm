"""REQ-37: nested conversation compact / summaries.

Compact replaces model context. Raw JSON + ChatMessage rows stay.
Nested compact sets parent_summary_id. No Neon, no secrets.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from swarm.core import chat_store
from swarm.core.chat_compact import (
    CompactError,
    build_model_context,
    compact_backlog,
    context_for_conversation,
    summarize_items,
)
from swarm.models import ChatConversation, ChatMessage, ConversationSummary


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="compact-op", password="pw")


@pytest.fixture
def client(user):
    c = Client()
    c.login(username="compact-op", password="pw")
    return c


def _turns(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"role": role, "content": content} for role, content in pairs]


def _seed_json(user, agent, messages, conversation_id):
    chat_store.save(
        chat_store.user_key_for(user),
        agent,
        messages,
        conversation_id=conversation_id,
    )


@pytest.mark.django_db
def test_compact_replaces_model_context(user):
    cid = "conv-compact-ctx"
    messages = _turns(
        ("user", "alpha question"),
        ("assistant", "alpha answer"),
        ("user", "beta question"),
        ("assistant", "beta answer"),
    )
    _seed_json(user, "jeeves", messages, cid)
    row, raw = compact_backlog(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=messages,
    )
    assert raw == messages
    context = build_model_context(raw, [row])
    joined = " ".join(m["content"] for m in context)
    assert "alpha question" not in joined
    assert "[Conversation summary]" in joined
    assert context[0]["role"] == "system"
    assert all(m.get("content") != "alpha question" for m in context)


@pytest.mark.django_db
def test_nested_compact_sets_parent_summary_id(user):
    cid = "conv-compact-nest"
    first = _turns(("user", "one"), ("assistant", "two"))
    _seed_json(user, "codey", first, cid)
    s1, _ = compact_backlog(user=user, conversation_id=cid, agent_id="codey", messages=first)
    assert s1.parent_summary_id is None

    later = first + _turns(("user", "three"), ("assistant", "four"))
    s2, raw = compact_backlog(user=user, conversation_id=cid, agent_id="codey", messages=later)
    assert s2.parent_summary_id == s1.id
    assert s2.span == {"start": 0, "end": 3}
    assert raw == later

    context = context_for_conversation(cid, later)
    joined = "\n".join(m["content"] for m in context)
    assert "[Conversation summary]" in joined
    assert "[nested summary]" in joined
    assert "three" not in joined


@pytest.mark.django_db
def test_compact_keeps_raw_json_and_chatmessage_rows(user):
    cid = "conv-compact-raw"
    messages = _turns(("user", "keep me"), ("assistant", "still here"))
    _seed_json(user, "stewie", messages, cid)
    compact_backlog(user=user, conversation_id=cid, agent_id="stewie", messages=messages)

    loaded = chat_store.load(chat_store.user_key_for(user), "stewie")
    assert loaded is not None
    assert [m["content"] for m in loaded["messages"]] == ["keep me", "still here"]

    chat = ChatConversation.objects.get(conversation_id=cid)
    assert list(chat.chat_messages.values_list("content", flat=True)) == [
        "keep me",
        "still here",
    ]
    assert chat.summaries.count() == 1


@pytest.mark.django_db
def test_compact_endpoint_and_thread_payload(client, user):
    cid = "conv-compact-api"
    messages = _turns(("user", "remember this"), ("assistant", "ok"))
    _seed_json(user, "jeeves", messages, cid)

    resp = client.post(
        "/chat/compact/",
        data={
            "conversation_id": cid,
            "agent": "jeeves",
            "messages": messages,
        },
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["parent_summary_id"] is None
    assert body["summary"]["span"] == {"start": 0, "end": 1}
    assert body["raw_count"] == 2
    assert body["context"][0]["role"] == "system"
    assert "remember this" not in body["context"][0]["content"]

    thread = client.get(f"/chat/thread/?agent=jeeves&conversation_id={cid}")
    assert thread.status_code == 200
    payload = thread.json()
    assert payload["messages"][0]["content"] == "remember this"
    assert payload["summaries"][0]["id"] == body["summary"]["id"]
    assert payload["summaries"][0]["parent_summary_id"] is None


@pytest.mark.django_db
def test_compact_empty_rejected(client, user):
    resp = client.post(
        "/chat/compact/",
        data={"conversation_id": "empty-conv", "agent": "jeeves", "messages": []},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "Nothing to compact" in resp.json()["error"]


@pytest.mark.django_db
def test_compact_requires_login():
    resp = Client().post(
        "/chat/compact/",
        data={"conversation_id": "x", "agent": "jeeves"},
        content_type="application/json",
    )
    assert resp.status_code == 302
    assert "login" in resp["Location"]


@pytest.mark.django_db
def test_compact_does_not_delete_existing_chatmessages(user):
    cid = "conv-compact-keep-ids"
    chat = ChatConversation.objects.create(conversation_id=cid, student=user)
    first = ChatMessage.objects.create(conversation=chat, sender="user", content="original")
    ChatMessage.objects.create(conversation=chat, sender="assistant", content="reply")
    compact_backlog(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=_turns(("user", "original"), ("assistant", "reply")),
    )
    assert ChatMessage.objects.filter(pk=first.pk).exists()
    assert ChatMessage.objects.filter(conversation=chat).count() == 2


def test_summarize_items_is_extractive_no_secrets():
    body = summarize_items(
        [
            {"kind": "message", "role": "user", "content": "plain question"},
            {"kind": "summary", "body": "earlier digest"},
        ]
    )
    assert "plain question" in body
    assert "[summary] earlier digest" in body
    assert "sk-" not in body
    assert "api_key" not in body


@pytest.mark.django_db
def test_second_compact_mixes_summary_and_raw(user):
    cid = "conv-compact-mix"
    first = _turns(("user", "a"), ("assistant", "b"))
    s1, _ = compact_backlog(user=user, conversation_id=cid, agent_id="x", messages=first)
    later = first + _turns(("user", "fresh turn"), ("assistant", "fresh reply"))
    s2, _ = compact_backlog(user=user, conversation_id=cid, agent_id="x", messages=later)
    assert s2.parent_summary_id == s1.id
    assert "fresh turn" in s2.body
    assert "[summary]" in s2.body
    assert ConversationSummary.objects.filter(conversation_id=cid).count() == 2


@pytest.mark.django_db
def test_compact_error_on_foreign_conversation(user, db):
    other = get_user_model().objects.create_user(username="other-op", password="pw")
    ChatConversation.objects.create(conversation_id="owned-by-other", student=other)
    with pytest.raises(CompactError) as exc:
        compact_backlog(
            user=user,
            conversation_id="owned-by-other",
            agent_id="jeeves",
            messages=_turns(("user", "nope"), ("assistant", "no")),
        )
    assert exc.value.status == 403
