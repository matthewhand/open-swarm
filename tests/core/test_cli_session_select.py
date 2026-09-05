"""REQ-104 — list / switch CLI sessions (design A + honest degrade)."""

from __future__ import annotations

import json
import sys

from swarm.core import agent_settings as settings_store
from swarm.core import chat_store
from swarm.core.cli_catalog import can_list_sessions, list_sessions_argv
from swarm.core.cli_session_select import (
    PRIOR_HISTORY_KIND,
    format_prior_history,
    list_cli_sessions,
    parse_provider_sessions,
    remember_recent_session,
    select_cli_session,
    switch_notice_text,
)
from swarm.core.cli_sessions import get_cli_session


def _list_config(script: str) -> dict:
    return {
        "cli_agents": {
            "echo": {
                "cmd": [sys.executable, script, "{prompt}"],
                "parse": "json:.result",
                "resume_argv": ["--resume", "{session_id}"],
                "list_argv": [sys.executable, script, "--list"],
            }
        }
    }


def test_catalog_clis_cannot_list_by_default():
    for name in ("grok", "claude", "gemini", "codex", "opencode", "agy", "pi"):
        assert can_list_sessions(name) is False
        assert list_sessions_argv(name) is None


def test_parse_provider_sessions_sanitizes_and_skips_secrets():
    raw = json.dumps(
        [
            {"id": "sid-ok", "title": "Alpha", "snippet": "hi", "updated_at": "2026-09-05T12:00:00Z"},
            {"id": "sk-secret-key", "title": "nope"},
            {"session_id": "sid-two", "name": "Beta"},
        ]
    )
    rows = parse_provider_sessions(raw)
    assert [r["id"] for r in rows] == ["sid-ok", "sid-two"]
    assert rows[0]["source"] == "provider"


def test_list_fixture_cli_returns_n_sessions(tmp_path):
    script = tmp_path / "list_cli.py"
    script.write_text(
        "import json, sys\n"
        "if '--list' in sys.argv:\n"
        "    print(json.dumps([\n"
        "        {'id': 'sid-1', 'title': 'First', 'snippet': 'hello', 'updated_at': '2026-09-05T10:00:00Z'},\n"
        "        {'id': 'sid-2', 'title': 'Second', 'snippet': 'again', 'updated_at': '2026-09-05T11:00:00Z'},\n"
        "        {'id': 'sid-3', 'title': 'Third', 'snippet': 'more', 'updated_at': '2026-09-05T12:00:00Z'},\n"
        "    ]))\n"
        "    raise SystemExit(0)\n"
        "print(json.dumps({'result': 'ok'}))\n"
    )
    payload = list_cli_sessions(
        "u1",
        "cli_agent",
        "echo",
        config=_list_config(str(script)),
        base_dir=tmp_path,
    )
    assert payload["can_list"] is True
    assert [row["id"] for row in payload["sessions"]] == ["sid-3", "sid-2", "sid-1"]
    assert payload["empty_reason"] is None
    assert payload["activity_sot"] == "provider"


def test_non_listable_cli_degrades_honestly(tmp_path):
    payload = list_cli_sessions("u1", "cli_agent", "grok", config={}, base_dir=tmp_path)
    assert payload["can_list"] is False
    assert payload["sessions"] == []
    assert payload["empty_reason"] == "This CLI can't list sessions"
    remember_recent_session(
        "u1",
        "cli_agent",
        "grok",
        "sid-recent",
        title="Touched",
        snippet="last send",
        base_dir=tmp_path,
    )
    again = list_cli_sessions("u1", "cli_agent", "grok", config={}, base_dir=tmp_path)
    assert again["can_list"] is False
    assert [row["id"] for row in again["sessions"]] == ["sid-recent"]
    assert again["activity_sot"] == "swarm"
    assert again["empty_reason"] is None


def test_select_updates_stored_id_and_mints_new_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    settings_store.reset_agent_settings_cache()
    chat_store.save(
        "u1",
        "cli_agent",
        [
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
            {"role": "status", "content": "Started a new echo session."},
        ],
        conversation_id="agt-1-cli_agent",
        base_dir=tmp_path,
    )
    first = select_cli_session(
        "u1",
        "cli_agent",
        "echo",
        session_id="sid-2",
        from_conversation_id="agt-1-cli_agent",
        imported_messages=[{"role": "user", "content": "from cli"}, {"role": "assistant", "content": "cli reply"}],
        title="Second",
        snippet="again",
        base_dir=tmp_path,
    )
    assert first["same_session"] is False
    assert first["conversation_id"] != "agt-1-cli_agent"
    assert first["conversation_id"].startswith("cli-cli_agent-")
    assert first["cli_session_id"] == "sid-2"
    assert first["collapsed_prior"] is True
    assert first["import"] == "full"
    assert "Restored" not in first["status"]
    assert first["status"] == "Switched to echo session sid-2."
    assert get_cli_session("u1", "cli_agent", "echo", base_dir=tmp_path) == "sid-2"
    assert settings_store.stored_cli_session_id("cli_agent") == "sid-2"

    kinds = [m.get("kind") for m in first["messages"]]
    assert PRIOR_HISTORY_KIND in kinds
    pill = next(m for m in first["messages"] if m.get("kind") == PRIOR_HISTORY_KIND)
    assert "old question" in pill["content"]
    assert "old answer" in pill["content"]
    assert any(m.get("content") == "from cli" for m in first["messages"])
    assert not any(m.get("role") in ("status", "info") for m in first["turns"])
    assert any(e.get("content") == first["status"] for e in first["ui_events"])
    assert any(e.get("kind") == PRIOR_HISTORY_KIND for e in first["ui_events"])

    old = chat_store.load("u1", "cli_agent", conversation_id="agt-1-cli_agent", base_dir=tmp_path)
    assert old is not None
    assert any(m.get("content") == "old question" for m in old["messages"])

    new = chat_store.load(
        "u1",
        "cli_agent",
        conversation_id=first["conversation_id"],
        session_id=first["conversation_id"],
        base_dir=tmp_path,
    )
    assert new is not None
    assert new["conversation_id"] == first["conversation_id"]
    assert not any(m.get("role") in ("status", "info") for m in new["messages"])
    assert any(e.get("content") == first["status"] for e in new["ui_events"])
    assert any(e.get("kind") == PRIOR_HISTORY_KIND for e in new["ui_events"])


def test_select_same_session_does_not_double_collapse(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    settings_store.reset_agent_settings_cache()
    chat_store.save(
        "u1",
        "cli_agent",
        [{"role": "user", "content": "hi"}],
        conversation_id="cur",
        cli_sessions={"echo": "sid-1"},
        base_dir=tmp_path,
    )
    again = select_cli_session(
        "u1",
        "cli_agent",
        "echo",
        session_id="sid-1",
        from_conversation_id="cur",
        base_dir=tmp_path,
    )
    assert again["same_session"] is True
    assert again["collapsed_prior"] is False
    assert again["conversation_id"] == "cur"


def test_start_new_clears_id_and_collapses_prior(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    settings_store.reset_agent_settings_cache()
    chat_store.save(
        "u1",
        "cli_agent",
        [{"role": "user", "content": "keep me"}, {"role": "assistant", "content": "ok"}],
        conversation_id="old",
        cli_sessions={"echo": "sid-1"},
        base_dir=tmp_path,
    )
    result = select_cli_session(
        "u1",
        "cli_agent",
        "echo",
        start_new=True,
        from_conversation_id="old",
        base_dir=tmp_path,
    )
    assert result["cli_session_id"] is None
    assert result["collapsed_prior"] is True
    assert result["status"] == "Started a new echo session."
    assert "Restored" not in result["status"]
    assert get_cli_session("u1", "cli_agent", "echo", base_dir=tmp_path) is None
    assert settings_store.stored_cli_session_id("cli_agent") is None
    assert any(m.get("kind") == PRIOR_HISTORY_KIND for m in result["messages"])
    assert not any(m.get("role") in ("status", "info") for m in result["turns"])
    assert any(e.get("content") == result["status"] for e in result["ui_events"])


def test_old_compressions_are_not_copied(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    settings_store.reset_agent_settings_cache()
    chat_store.save(
        "u1",
        "cli_agent",
        [
            {"role": "user", "content": "summarized turn"},
            {"role": "assistant", "content": "long answer"},
        ],
        conversation_id="compacted",
        base_dir=tmp_path,
    )
    result = select_cli_session(
        "u1",
        "cli_agent",
        "echo",
        session_id="sid-new",
        from_conversation_id="compacted",
        base_dir=tmp_path,
    )
    assert result["conversation_id"] != "compacted"
    # New thread has the pill + status only — no copied summary rows.
    roles = [m.get("role") for m in result["messages"]]
    assert "assistant" not in roles
    assert any(m.get("kind") == PRIOR_HISTORY_KIND for m in result["messages"])


def test_rejects_secret_shaped_paste(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_CHAT_DIR", str(tmp_path))
    try:
        select_cli_session(
            "u1",
            "cli_agent",
            "echo",
            session_id="sk-live-secret-key",
            base_dir=tmp_path,
        )
    except ValueError as exc:
        assert "session id" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_switch_notice_never_says_restored():
    assert "restored" not in switch_notice_text("echo", "sid-1", start_new=False).lower()
    assert "restored" not in switch_notice_text("echo", None, start_new=True).lower()


def test_format_prior_history_skips_empty():
    text = format_prior_history(
        [
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "a"},
            {"role": "status", "content": "Started a new echo session."},
        ]
    )
    assert "**User:** q" in text
    assert "**Assistant:** a" in text
    assert "Started a new echo session." not in text
