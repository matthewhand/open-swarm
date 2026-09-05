"""REQ-105: Django-backed sessions scoped to one agent."""

from django.contrib.auth import get_user_model

from swarm.core import chat_store
from swarm.core.agent_sessions import (
    DEFAULT_TITLE,
    NEW_TITLE,
    create_empty_session,
    ensure_default_session,
    list_agent_sessions,
    persist_allocated_session,
    title_and_snippet,
)
from swarm.core.chat_compact import compact_backlog
from swarm.models import ConversationSummary


def _user(db, name="sess-op"):
    return get_user_model().objects.create_user(username=name, password="pw")


def test_title_and_snippet_ignore_status_lines():
    title, snippet = title_and_snippet(
        [
            {"role": "status", "content": "Connecting…"},
            {"role": "user", "content": "first question about bees"},
            {"role": "assistant", "content": "bees make honey"},
        ]
    )
    assert title.startswith("first question")
    assert snippet == "bees make honey"


def test_default_session_migrates_existing_transcript(db, tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    user = _user(db)
    cid = chat_store.conversation_id_for(user, "codey")
    chat_store.save(
        chat_store.user_key_for(user),
        "codey",
        [{"role": "user", "content": "remember this"}, {"role": "assistant", "content": "ok"}],
        conversation_id=cid,
    )
    row = ensure_default_session(user, "codey")
    assert row.conversation_id == cid
    assert row.agent_id == "codey"
    assert row.title == "remember this"
    assert row.snippet == "ok"
    listed = list_agent_sessions(user, "codey")
    assert [item.conversation_id for item in listed] == [cid]


def test_create_n_sessions_lists_only_that_agent(db, tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    user = _user(db)
    ensure_default_session(user, "codey")
    a = create_empty_session(user, "codey", title="Notes")
    b = create_empty_session(user, "codey", title="Later")
    other = create_empty_session(user, "stewie", title="Other")
    ids = {row.conversation_id for row in list_agent_sessions(user, "codey")}
    assert a.conversation_id in ids
    assert b.conversation_id in ids
    assert other.conversation_id not in ids
    assert all(row.agent_id == "codey" for row in list_agent_sessions(user, "codey"))
    empty = create_empty_session(user, "codey")
    assert empty.title == NEW_TITLE
    assert empty.snippet == ""


def test_scale_out_allocate_appears_in_picker(db, tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    user = _user(db, "scale-op")
    persist_allocated_session(user, "worker", "task-1-worker-alpha", empty=True)
    persist_allocated_session(user, "worker", "task-1-worker-beta", empty=True)
    ids = {row.conversation_id for row in list_agent_sessions(user, "worker")}
    assert "task-1-worker-alpha" in ids
    assert "task-1-worker-beta" in ids


def test_compact_does_not_leak_across_sessions(db, tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    user = _user(db, "compact-sess")
    first = create_empty_session(user, "jeeves", title="Alpha")
    second = create_empty_session(user, "jeeves", title="Beta")
    messages = [
        {"role": "user", "content": "alpha question"},
        {"role": "assistant", "content": "alpha answer"},
    ]
    compact_backlog(
        user=user,
        conversation_id=first.conversation_id,
        agent_id="jeeves",
        messages=messages,
        summarizer=lambda items, **_kwargs: "LLM digest of the compacted range.",
    )
    assert ConversationSummary.objects.filter(conversation_id=first.conversation_id).exists()
    assert not ConversationSummary.objects.filter(conversation_id=second.conversation_id).exists()
    assert DEFAULT_TITLE or first.title
