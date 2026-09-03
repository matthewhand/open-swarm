"""Settings-only chat persistence + retention (REQ-14)."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from swarm.core import chat_store
from swarm.models import ChatConversation, ChatMessage


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="chat-op", password="pw")


@pytest.fixture
def client(user):
    c = Client()
    c.login(username="chat-op", password="pw")
    return c


def _seed_thread(user, agent="jeeves", content="hello"):
    chat_store.save(
        chat_store.user_key_for(user),
        agent,
        [{"role": "user", "content": content}, {"role": "assistant", "content": "ok"}],
        conversation_id=chat_store.conversation_id_for(user, agent),
    )


@pytest.mark.django_db
def test_settings_shows_chat_counts_and_disk(client, user):
    _seed_thread(user)
    html = client.get("/settings/").content.decode()
    assert "Chat persistence" in html
    assert "Chats" in html
    assert "Disk used" in html
    assert "SWARM_CHAT_MAX_AGE_DAYS" in html
    assert "jeeves" in html
    assert 'data-action="chat-archive-all"' in html
    assert 'data-action="chat-empty-trash"' in html
    assert "Move to trash" in html
    # Must stay off the Chat chrome contract.
    assert "onclick=" not in html


@pytest.mark.django_db
def test_settings_unauthenticated_redirects():
    resp = Client().get("/settings/")
    assert resp.status_code == 302
    assert "login" in resp["Location"]


@pytest.mark.django_db
def test_chat_thread_restores_json(client, user):
    _seed_thread(user, "codey", "remember this")
    resp = client.get("/chat/thread/?agent=codey")
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_id"] == "codey"
    assert body["conversation_id"] == chat_store.conversation_id_for(user, "codey")
    assert body["messages"][0]["content"] == "remember this"
    assert body["messages"][1]["role"] == "assistant"


@pytest.mark.django_db
def test_chat_thread_backfills_from_django_db(client, user):
    cid = chat_store.conversation_id_for(user, "hybrid_team")
    chat = ChatConversation.objects.create(conversation_id=cid, student=user)
    ChatMessage.objects.create(conversation=chat, sender="user", content="from-db")
    resp = client.get("/chat/thread/?agent=hybrid_team")
    assert resp.status_code == 200
    assert resp.json()["messages"][0]["content"] == "from-db"
    loaded = chat_store.load(chat_store.user_key_for(user), "hybrid_team")
    assert loaded is not None
    assert loaded["messages"][0]["content"] == "from-db"


@pytest.mark.django_db
def test_chat_thread_requires_login():
    resp = Client().get("/chat/thread/?agent=jeeves")
    assert resp.status_code == 302


@pytest.mark.django_db
def test_archive_one_and_restore(client, user):
    _seed_thread(user, "jeeves")
    resp = client.post("/settings/chats/action/", {"action": "archive", "agent_id": "jeeves"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert chat_store.load(chat_store.user_key_for(user), "jeeves") is None

    resp = client.post("/settings/chats/action/", {"action": "restore", "agent_id": "jeeves"})
    assert resp.status_code == 200
    loaded = chat_store.load(chat_store.user_key_for(user), "jeeves")
    assert loaded is not None
    assert loaded["messages"][0]["content"] == "hello"


@pytest.mark.django_db
def test_archive_all_and_empty_trash(client, user):
    _seed_thread(user, "a")
    _seed_thread(user, "b")
    resp = client.post("/settings/chats/action/", {"action": "archive_all"})
    assert resp.status_code == 200
    assert sorted(resp.json()["archived"]) == ["a", "b"]
    stats = chat_store.stats(chat_store.user_key_for(user))
    assert stats["active_count"] == 0
    assert stats["trash_count"] == 2

    resp = client.post("/settings/chats/action/", {"action": "empty_trash"})
    assert resp.status_code == 200
    assert resp.json()["removed"] == 2
    assert chat_store.stats(chat_store.user_key_for(user))["trash_count"] == 0


@pytest.mark.django_db
def test_unknown_action_rejected(client):
    resp = client.post("/settings/chats/action/", {"action": "explode"})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_retention_scoped_to_current_user(client, user, db):
    other = get_user_model().objects.create_user(username="other", password="pw")
    _seed_thread(other, "other-user-thread", "private-other-transcript")
    _seed_thread(user, "mine-thread", "visible-own-transcript")
    html = client.get("/settings/").content.decode()
    assert "mine-thread" in html
    assert "other-user-thread" not in html
    client.post("/settings/chats/action/", {"action": "archive_all"})
    assert chat_store.load(chat_store.user_key_for(other), "other-user-thread") is not None
    assert chat_store.load(chat_store.user_key_for(user), "mine-thread") is None


@pytest.mark.django_db
def test_consumer_save_writes_json(user):
    from swarm.consumers import DjangoChatConsumer

    consumer = DjangoChatConsumer()
    consumer.user = user
    consumer.active_agent = "jeeves"
    save_sync = DjangoChatConsumer.__dict__["save_conversation"].func
    save_sync(
        consumer,
        chat_store.conversation_id_for(user, "jeeves"),
        [{"role": "user", "content": "via-ws"}, {"role": "assistant", "content": "ack"}],
    )
    loaded = chat_store.load(chat_store.user_key_for(user), "jeeves")
    assert loaded is not None
    assert loaded["messages"][0]["content"] == "via-ws"


@pytest.mark.django_db
def test_settings_chat_group_lists_env_vars(client):
    html = client.get("/settings/").content.decode()
    assert "SWARM_CHAT_DIR" in html
    start = html.find("id=\"swarm-settings-data\"")
    assert start != -1
    payload = html[html.find(">", start) + 1 : html.find("</script>", start)]
    data = json.loads(payload)
    assert "chat_persistence" in data
    assert "SWARM_CHAT_MAX_AGE_DAYS" in data["chat_persistence"]["settings"]
