"""Unit tests for the file-backed Responses store (``swarm.core.responses_store``).

These exercise the persistence layer directly (no HTTP), including the
path-traversal guard on caller-supplied ids.
"""
from pathlib import Path

from swarm.core import responses_store


def test_save_load_roundtrip(tmp_path):
    record = {"id": "resp_abc123", "object": "response", "messages": [{"role": "user", "content": "hi"}]}
    responses_store.save(record, base_dir=tmp_path)
    loaded = responses_store.load("resp_abc123", base_dir=tmp_path)
    assert loaded == record


def test_load_missing_returns_none(tmp_path):
    assert responses_store.load("resp_nope", base_dir=tmp_path) is None


def test_delete_removes_record(tmp_path):
    responses_store.save({"id": "resp_del1"}, base_dir=tmp_path)
    assert responses_store.delete("resp_del1", base_dir=tmp_path) is True
    assert responses_store.load("resp_del1", base_dir=tmp_path) is None
    # Second delete is a no-op.
    assert responses_store.delete("resp_del1", base_dir=tmp_path) is False


def test_save_invalid_id_is_noop(tmp_path):
    # Ids that don't match the resp_ pattern are silently dropped (never written).
    responses_store.save({"id": "../escape"}, base_dir=tmp_path)
    responses_store.save({"id": ""}, base_dir=tmp_path)
    assert list(tmp_path.glob("*")) == []


def test_load_rejects_traversal_ids(tmp_path):
    # A planted file outside the safe charset must never be reachable.
    evil = tmp_path / "secret.json"
    evil.write_text('{"id": "secret"}')
    assert responses_store.load("../secret", base_dir=tmp_path) is None
    assert responses_store.load("resp_../secret", base_dir=tmp_path) is None
    assert responses_store.delete("../secret", base_dir=tmp_path) is False


def test_store_dir_honors_env(monkeypatch, tmp_path):
    target = tmp_path / "custom"
    monkeypatch.setenv("SWARM_RESPONSES_DIR", str(target))
    responses_store.save({"id": "resp_envcfg"}, base_dir=None)
    assert (target / "resp_envcfg.json").is_file()
    assert isinstance(responses_store._store_dir(), Path)
