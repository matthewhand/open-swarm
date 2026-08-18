"""Unit tests for the file-backed cancel registry (cross-worker shared cancel)."""

from __future__ import annotations

from pathlib import Path

from swarm.core import cancel_registry


def test_request_then_is_cancel_requested(tmp_path: Path) -> None:
    rid = "resp_cancel_ok1"
    assert cancel_registry.request_cancel(rid, base_dir=tmp_path) is True
    assert cancel_registry.is_cancel_requested(rid, base_dir=tmp_path) is True
    flag = tmp_path / "cancel" / f"{rid}.flag"
    assert flag.is_file()


def test_clear_then_false(tmp_path: Path) -> None:
    rid = "resp_cancel_clear1"
    cancel_registry.request_cancel(rid, base_dir=tmp_path)
    assert cancel_registry.is_cancel_requested(rid, base_dir=tmp_path) is True
    cancel_registry.clear_cancel(rid, base_dir=tmp_path)
    assert cancel_registry.is_cancel_requested(rid, base_dir=tmp_path) is False
    assert not (tmp_path / "cancel" / f"{rid}.flag").exists()


def test_invalid_response_ids_rejected_safely(tmp_path: Path) -> None:
    for bad in ("", "../escape", "resp_../x", "secret", "resp_", "not_resp_id"):
        assert cancel_registry.request_cancel(bad, base_dir=tmp_path) is False
        assert cancel_registry.is_cancel_requested(bad, base_dir=tmp_path) is False
        cancel_registry.clear_cancel(bad, base_dir=tmp_path)  # no-op, no raise
    # Nothing written under store (or only an empty cancel dir is ok if mkdir raced — expect none)
    assert list(tmp_path.iterdir()) == []


def test_filesystem_visible_without_local_cache(tmp_path: Path) -> None:
    """Simulate another worker: flag on disk, empty process-local set."""
    rid = "resp_cross_worker1"
    flag = tmp_path / "cancel" / f"{rid}.flag"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("", encoding="utf-8")
    with cancel_registry._local_lock:
        cancel_registry._local.discard(rid)
    assert cancel_registry.is_cancel_requested(rid, base_dir=tmp_path) is True


def test_honors_swarm_responses_dir(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "shared"
    monkeypatch.setenv("SWARM_RESPONSES_DIR", str(target))
    rid = "resp_env_cancel1"
    assert cancel_registry.request_cancel(rid) is True
    assert (target / "cancel" / f"{rid}.flag").is_file()
    assert cancel_registry.is_cancel_requested(rid) is True
    cancel_registry.clear_cancel(rid)
    assert not (target / "cancel" / f"{rid}.flag").exists()
