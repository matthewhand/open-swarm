"""REQ-65 session policy: reuse vs new chat per task."""

from types import SimpleNamespace

from swarm.core import agent_settings as settings_store
from swarm.core import chat_store
from swarm.core import session_policy as policy


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    settings_store.reset_agent_settings_cache()
    policy.clear_active_sessions()
    return tmp_path / "chats"


def test_off_reuses_session_id(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    user = SimpleNamespace(pk=7)
    first = policy.allocate_task_session(user, "worker")
    second = policy.allocate_task_session(user, "worker")
    assert first.new_chat_per_task is False
    assert first.empty is False
    assert first.resume_external is True
    assert first.conversation_id == second.conversation_id
    assert first.conversation_id == chat_store.conversation_id_for(user, "worker")


def test_on_mints_new_session_per_task(tmp_path, monkeypatch):
    chats = _isolate(tmp_path, monkeypatch)
    settings_store.update_settings("worker", {"new_chat_per_task": True})
    user = SimpleNamespace(pk=7)
    a = policy.allocate_task_session(user, "worker", task_id="one")
    b = policy.allocate_task_session(user, "worker", task_id="two")
    assert a.new_chat_per_task is True
    assert a.empty is True
    assert a.resume_external is False
    assert a.conversation_id != b.conversation_id
    assert a.conversation_id != chat_store.conversation_id_for(user, "worker")

    chat_store.save(
        "u7",
        "worker",
        [{"role": "user", "content": "task-a"}],
        conversation_id=a.conversation_id,
        session_id=a.conversation_id,
        base_dir=chats,
    )
    chat_store.save(
        "u7",
        "worker",
        [{"role": "user", "content": "task-b"}],
        conversation_id=b.conversation_id,
        session_id=b.conversation_id,
        base_dir=chats,
    )
    loaded_a = chat_store.load(
        "u7", "worker", session_id=a.conversation_id, base_dir=chats
    )
    loaded_b = chat_store.load(
        "u7", "worker", session_id=b.conversation_id, base_dir=chats
    )
    assert loaded_a["messages"][0]["content"] == "task-a"
    assert loaded_b["messages"][0]["content"] == "task-b"
    sessions = policy.list_active_task_sessions("u7", "worker")
    assert a.conversation_id in sessions
    assert b.conversation_id in sessions


def test_cli_and_api_do_not_resume_when_on(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    settings_store.update_settings("claude", {"new_chat_per_task": True})
    settings_store.set_cli_session_id("claude", "sess-old")
    settings_store.set_remote_session_id("hermes", "remote-old")
    settings_store.update_settings("hermes", {"new_chat_per_task": True})
    assert policy.resume_cli_session_id("claude", "sess-old") is None
    assert policy.resume_remote_session_id("hermes", "remote-old") is None
    assert policy.continue_api_previous_response("claude", "resp_prior") is None
    assert policy.messages_for_task("claude", [{"role": "user", "content": "hi"}]) == []

    settings_store.update_settings("reuse", {"new_chat_per_task": False})
    settings_store.set_cli_session_id("reuse", "sess-keep")
    assert policy.resume_cli_session_id("reuse") == "sess-keep"
    assert policy.continue_api_previous_response("reuse", "resp_prior") == "resp_prior"
