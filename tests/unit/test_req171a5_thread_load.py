"""REQ-171A-5 / #605 — HTTP GET and WS fetch share JSON-first load.

Reload via ``GET /chat/thread/`` and reconnect via ``fetch_conversation``
must return the same transcript, including ``ts`` and ``edited``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from swarm.consumers import DjangoChatConsumer, _conversation_cache_key
from swarm.core import chat_store
from swarm.core.thread_load import load_thread
from swarm.models import ChatConversation, ChatMessage

REPO = Path(__file__).resolve().parents[2]
THREAD_LOAD = REPO / "src" / "swarm" / "core" / "thread_load.py"
CONSUMERS = REPO / "src" / "swarm" / "consumers.py"
CHAT_VIEWS = REPO / "src" / "swarm" / "views" / "chat_persist_views.py"
WS_DOC = REPO / "docs" / "websocket_chat.md"
CI = REPO / ".github" / "workflows" / "req171a5-thread-load.yml"

TS = "2026-09-02T21:21:00+00:00"
EDITED_CONTENT = "engineered context"


def test_source_lock_shared_json_first_load_order():
    """One documented load order: JSON first, DB backfill, both HTTP and WS."""
    helper = THREAD_LOAD.read_text(encoding="utf-8")
    assert "Load order (JSON is the source of truth)" in helper
    assert "chat_store.load" in helper
    assert "messages_from_db" in helper
    assert "def load_thread" in helper

    ws = CONSUMERS.read_text(encoding="utf-8")
    assert "from swarm.core.thread_load import load_thread" in ws
    fetch = ws.split("def fetch_conversation", 1)[1].split("def save_conversation", 1)[0]
    assert "load_thread(" in fetch
    assert "JSON disk (source of truth)" in fetch
    assert 'raw = [{\'role\': m[\'sender\'], \'content\': m[\'content\']}' not in fetch

    http = CHAT_VIEWS.read_text(encoding="utf-8")
    assert "from swarm.core.thread_load import load_thread" in http
    assert "JSON first, Django backfill" in http

    doc = WS_DOC.read_text(encoding="utf-8")
    assert "JSON first" in doc
    assert "DB backfill" in doc

    ci = CI.read_text(encoding="utf-8")
    assert "own-diff" in ci
    assert "neon" not in ci.lower()
    assert ":8001" not in helper
    assert ":8001" not in ws
    assert ":8001" not in ci


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="thread-load-op", password="pw")


@pytest.fixture
def client(user):
    c = Client()
    c.login(username="thread-load-op", password="pw")
    return c


def _seed_json_with_ts_edited(user, agent="codey"):
    cid = chat_store.conversation_id_for(user, agent)
    chat_store.save(
        chat_store.user_key_for(user),
        agent,
        [
            {
                "role": "user",
                "content": EDITED_CONTENT,
                "ts": TS,
                "edited": True,
            },
            {
                "role": "assistant",
                "content": "ok",
                "ts": "2026-09-02T21:21:01+00:00",
            },
        ],
        conversation_id=cid,
    )
    # Stripped Django mirror — WS used to prefer these and drop ts/edited.
    chat = ChatConversation.objects.create(
        conversation_id=cid,
        student=user,
        agent_id=agent,
    )
    ChatMessage.objects.create(conversation=chat, sender="user", content=EDITED_CONTENT)
    ChatMessage.objects.create(conversation=chat, sender="assistant", content="ok")
    return cid


def _fetch_sync(user, conversation_id, agent="codey"):
    consumer = DjangoChatConsumer()
    consumer.user = user
    consumer.default_blueprint = agent
    consumer.active_agent = agent
    consumer.conversation_id = conversation_id
    consumer.messages = []
    consumer.ui_events = []
    fetch_sync = DjangoChatConsumer.__dict__["fetch_conversation"].func
    return fetch_sync(consumer, conversation_id)


@pytest.mark.django_db
def test_fetch_conversation_keeps_json_ts_and_edited_and_matches_http(
    client, user, tmp_path, monkeypatch
):
    """JSON with ts+edited survives WS fetch; HTTP GET matches."""
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path / "chats"))
    cid = _seed_json_with_ts_edited(user)

    fetched = _fetch_sync(user, cid)
    assert fetched[0]["content"] == EDITED_CONTENT
    assert fetched[0]["ts"] == TS
    assert fetched[0]["edited"] is True
    assert fetched[1]["content"] == "ok"
    assert fetched[1]["ts"] == "2026-09-02T21:21:01+00:00"

    resp = client.get(f"/chat/thread/?agent=codey&conversation_id={cid}")
    assert resp.status_code == 200
    http_messages = resp.json()["messages"]
    assert [row["content"] for row in http_messages] == [row["content"] for row in fetched]
    assert http_messages[0]["ts"] == fetched[0]["ts"] == TS
    assert http_messages[0]["edited"] is True
    assert fetched[0]["edited"] is True
    assert http_messages[1]["ts"] == fetched[1]["ts"]


@pytest.mark.django_db
def test_load_thread_prefers_json_over_stripped_db(user, tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path / "chats"))
    cid = _seed_json_with_ts_edited(user, "jeeves")
    loaded = load_thread(
        user,
        "jeeves",
        requested_cid=cid,
        default_cid=cid,
    )
    assert loaded.from_json is True
    assert loaded.turns[0]["ts"] == TS
    assert loaded.turns[0]["edited"] is True


@pytest.mark.django_db
def test_cache_key_stays_composite_after_json_load(user, tmp_path, monkeypatch):
    from swarm.consumers import IN_MEMORY_CONVERSATIONS

    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path / "chats"))
    cid = _seed_json_with_ts_edited(user)
    _fetch_sync(user, cid)
    assert _conversation_cache_key(user, cid) in IN_MEMORY_CONVERSATIONS
    assert cid not in IN_MEMORY_CONVERSATIONS
