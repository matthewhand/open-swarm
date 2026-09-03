"""Unit tests for the per-agent chat JSON store (REQ-14)."""

from datetime import datetime, timedelta, timezone

from swarm.core import chat_store


def test_save_load_roundtrip(tmp_path):
    path = chat_store.save(
        "u1",
        "jeeves",
        [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
        conversation_id="agt-1-jeeves",
        base_dir=tmp_path,
    )
    assert path is not None
    assert path == tmp_path / "active" / "u1" / "jeeves.json"
    loaded = chat_store.load("u1", "jeeves", base_dir=tmp_path)
    assert loaded is not None
    assert loaded["agent_id"] == "jeeves"
    assert loaded["conversation_id"] == "agt-1-jeeves"
    assert [m["content"] for m in loaded["messages"]] == ["hi", "hello"]


def test_normalize_and_default_agent():
    assert chat_store.normalize_agent_id(None) == "_default"
    assert chat_store.normalize_agent_id("  ") == "_default"
    assert chat_store.normalize_agent_id("hybrid_team") == "hybrid_team"


def test_normalize_keeps_status_role(tmp_path):
    chat_store.save(
        "u1",
        "cli_agent",
        [
            {"role": "status", "content": "CLI: antigravity → grok"},
            {"role": "user", "content": "hi"},
        ],
        base_dir=tmp_path,
    )
    loaded = chat_store.load("u1", "cli_agent", base_dir=tmp_path)
    assert loaded["messages"][0] == {"role": "status", "content": "CLI: antigravity → grok"}
    assert loaded["messages"][1]["role"] == "user"
    assert chat_store.normalize_agent_id("../etc/passwd") == "etc-passwd"


def test_rejects_traversal_user_key(tmp_path):
    assert chat_store.save("../escape", "jeeves", [{"role": "user", "content": "x"}], base_dir=tmp_path) is None
    assert chat_store.load("../escape", "jeeves", base_dir=tmp_path) is None
    assert list(tmp_path.glob("**/*")) == []


def test_archive_then_restore(tmp_path):
    chat_store.save("u1", "codey", [{"role": "user", "content": "keep me"}], base_dir=tmp_path)
    dest = chat_store.archive("u1", "codey", base_dir=tmp_path)
    assert dest is not None
    assert dest.parent == tmp_path / "trash" / "u1"
    assert chat_store.load("u1", "codey", base_dir=tmp_path) is None
    assert chat_store.stats("u1", base_dir=tmp_path)["trash_count"] == 1

    restored = chat_store.restore("u1", "codey", base_dir=tmp_path)
    assert restored is not None
    loaded = chat_store.load("u1", "codey", base_dir=tmp_path)
    assert loaded["messages"][0]["content"] == "keep me"


def test_empty_trash_hard_deletes(tmp_path):
    chat_store.save("u1", "a", [{"role": "user", "content": "1"}], base_dir=tmp_path)
    chat_store.archive("u1", "a", base_dir=tmp_path)
    assert chat_store.empty_trash("u1", base_dir=tmp_path) == 1
    assert chat_store.list_trash("u1", base_dir=tmp_path) == []
    assert chat_store.restore("u1", "a", base_dir=tmp_path) is None


def test_prune_moves_old_to_trash_not_hard_delete(tmp_path):
    chat_store.save("u1", "old", [{"role": "user", "content": "stale"}], base_dir=tmp_path)
    chat_store.save("u1", "fresh", [{"role": "user", "content": "new"}], base_dir=tmp_path)
    old_path = tmp_path / "active" / "u1" / "old.json"
    record = chat_store._read_json(old_path)
    record["updated_at"] = "2020-01-01T00:00:00Z"
    chat_store._atomic_write(old_path, record)

    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    moved = chat_store.prune_expired("u1", max_age_days=90, base_dir=tmp_path, now=now)
    assert moved == ["old"]
    assert chat_store.load("u1", "old", base_dir=tmp_path) is None
    assert chat_store.load("u1", "fresh", base_dir=tmp_path) is not None
    assert chat_store.stats("u1", base_dir=tmp_path)["trash_count"] == 1


def test_prune_disabled_when_zero(tmp_path):
    chat_store.save("u1", "old", [{"role": "user", "content": "stale"}], base_dir=tmp_path)
    assert chat_store.prune_expired("u1", max_age_days=0, base_dir=tmp_path) == []
    assert chat_store.load("u1", "old", base_dir=tmp_path) is not None


def test_stats_counts_and_bytes(tmp_path):
    chat_store.save("u1", "a", [{"role": "user", "content": "hello world"}], base_dir=tmp_path)
    stats = chat_store.stats("u1", base_dir=tmp_path)
    assert stats["active_count"] == 1
    assert stats["trash_count"] == 0
    assert stats["bytes_used"] > 0
    assert stats["format"] == "json"
    assert stats["store_dir"] == str(tmp_path)
    assert "B" in stats["bytes_label"] or "KB" in stats["bytes_label"]


def test_store_dir_honors_env(monkeypatch, tmp_path):
    target = tmp_path / "custom-chats"
    monkeypatch.setenv("SWARM_CHAT_DIR", str(target))
    chat_store.save("u9", "_default", [{"role": "user", "content": "x"}])
    assert (target / "active" / "u9" / "_default.json").is_file()


def test_get_max_age_days_default_and_override(monkeypatch):
    monkeypatch.delenv("SWARM_CHAT_MAX_AGE_DAYS", raising=False)
    assert chat_store.get_max_age_days() == 90
    monkeypatch.setenv("SWARM_CHAT_MAX_AGE_DAYS", "0")
    assert chat_store.get_max_age_days() == 0
    monkeypatch.setenv("SWARM_CHAT_MAX_AGE_DAYS", "14")
    assert chat_store.get_max_age_days() == 14
    assert chat_store.get_max_age_days(override=7) == 7


def test_format_bytes():
    assert chat_store.format_bytes(0) == "0 B"
    assert chat_store.format_bytes(500) == "500 B"
    assert chat_store.format_bytes(2048) == "2.0 KB"


def test_user_key_and_conversation_id():
    class U:
        pk = 42

    assert chat_store.user_key_for(U()) == "u42"
    assert chat_store.conversation_id_for(U(), "jeeves") == "agt-42-jeeves"


def test_prune_uses_mtime_when_updated_at_missing(tmp_path):
    chat_store.save("u1", "aged", [{"role": "user", "content": "x"}], base_dir=tmp_path)
    path = tmp_path / "active" / "u1" / "aged.json"
    record = chat_store._read_json(path)
    record.pop("updated_at", None)
    chat_store._atomic_write(path, record)
    old = (datetime.now(timezone.utc) - timedelta(days=200)).timestamp()
    import os

    os.utime(path, (old, old))
    moved = chat_store.prune_expired(
        "u1",
        max_age_days=90,
        base_dir=tmp_path,
        now=datetime.now(timezone.utc),
    )
    assert moved == ["aged"]


def test_archive_all(tmp_path):
    chat_store.save("u1", "a", [{"role": "user", "content": "1"}], base_dir=tmp_path)
    chat_store.save("u1", "b", [{"role": "user", "content": "2"}], base_dir=tmp_path)
    assert sorted(chat_store.archive_all("u1", base_dir=tmp_path)) == ["a", "b"]
    assert chat_store.list_active("u1", base_dir=tmp_path) == []
    assert chat_store.stats("u1", base_dir=tmp_path)["trash_count"] == 2
