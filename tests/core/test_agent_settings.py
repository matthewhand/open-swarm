"""REQ-65 per-agent settings store — default off, persist toggle."""

from swarm.core import agent_settings as store


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    store.reset_agent_settings_cache()


def test_default_off(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    settings = store.get_settings("worker")
    assert settings["new_chat_per_task"] is False
    assert store.is_new_chat_per_task("worker") is False
    assert store.is_new_chat_per_task("") is False


def test_update_toggle_roundtrip(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    updated = store.update_settings("worker", {"new_chat_per_task": True})
    assert updated["new_chat_per_task"] is True
    store.reset_agent_settings_cache()
    assert store.is_new_chat_per_task("worker") is True
    assert store.get_settings("other")["new_chat_per_task"] is False
    assert store.get_settings("worker")["use_suggestions"] is False
    store.update_settings("worker", {"use_suggestions": True})
    assert store.is_use_suggestions("worker") is True
    assert store.is_use_suggestions("other") is False


def test_rejects_unknown_keys(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    try:
        store.update_settings("worker", {"remotes": True})
    except ValueError as exc:
        assert "Unknown" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_folder_persists_on_agent_record(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    updated = store.update_settings("cli_agent", {"folder": "/tmp/ws"})
    assert updated["folder"] == "/tmp/ws"
    store.reset_agent_settings_cache()
    assert store.get_settings("cli_agent")["folder"] == "/tmp/ws"
    assert store.get_settings("other")["folder"] is None
