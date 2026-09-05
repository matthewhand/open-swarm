"""Provider session stores — ids + display metadata only."""

from __future__ import annotations

from swarm.core.cli_session_stores import list_agy_conversations, list_store_sessions


def test_agy_store_uses_stem_and_mtime_never_opens_db(tmp_path):
    sid = "d1d8a55b-cc27-4dd4-bc62-2f73015960d2"
    path = tmp_path / f"{sid}.db"
    path.write_bytes(b"SQLite format 3 not a real db")
    (tmp_path / f"{sid}.db-wal").write_bytes(b"wal")
    rows = list_agy_conversations(tmp_path)
    assert [r["id"] for r in rows] == [sid]
    assert rows[0]["title"] == sid
    assert rows[0]["source"] == "provider"
    assert rows[0]["updated_at"].endswith("Z")


def test_agy_store_skips_secrets_and_non_db(tmp_path):
    (tmp_path / "sk-live-secret-key.db").write_bytes(b"x")
    (tmp_path / "readme.txt").write_text("hi")
    assert list_agy_conversations(tmp_path) == []


def test_unknown_store_kind_is_empty():
    assert list_store_sessions("not-a-store", "/tmp") == []


def test_missing_dir_is_empty(tmp_path):
    assert list_agy_conversations(tmp_path / "nope") == []
    assert list_agy_conversations(None) == []
