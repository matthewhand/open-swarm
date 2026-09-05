"""Tests for confined workdir resolution and auto-run cleanup."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from swarm.core.workdir import (
    AUTO_RUN_MARKER,
    WorkdirEscapeError,
    cleanup_run_workdir,
    get_workspaces_dir,
    is_auto_run_workdir,
    is_auto_workdir_request,
    looks_like_auto_run_name,
    prune_stale_run_workdirs,
    resolve_confined_workdir,
    unrestricted_workdir_allowed,
)


def test_absolute_path_outside_root_rejected(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    root.mkdir()
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))
    monkeypatch.delenv("ALLOW_UNRESTRICTED_WORKDIR", raising=False)
    outside = tmp_path / "outside" / "pwn"
    outside.mkdir(parents=True)

    with pytest.raises(WorkdirEscapeError, match="outside the workspaces root"):
        resolve_confined_workdir(str(outside))


def test_relative_path_under_root_ok(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))
    monkeypatch.delenv("ALLOW_UNRESTRICTED_WORKDIR", raising=False)

    resolved = resolve_confined_workdir("demo/run1")
    assert resolved == (root / "demo" / "run1").resolve()
    assert resolved.is_dir()
    assert resolved.is_relative_to(root.resolve())


def test_parent_escape_rejected(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    root.mkdir()
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))
    monkeypatch.delenv("ALLOW_UNRESTRICTED_WORKDIR", raising=False)

    with pytest.raises(WorkdirEscapeError, match="escapes"):
        resolve_confined_workdir("../outside")


def test_unset_defaults_to_per_run_temp(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))

    a = resolve_confined_workdir(None, prune_stale=False)
    b = resolve_confined_workdir("", prune_stale=False)
    assert a.is_dir() and b.is_dir()
    assert a != b
    assert a.is_relative_to(root.resolve())
    assert b.is_relative_to(root.resolve())
    assert a.name.startswith("run-")
    assert (a / AUTO_RUN_MARKER).is_file()
    assert (b / AUTO_RUN_MARKER).is_file()
    assert is_auto_run_workdir(a)
    assert is_auto_workdir_request(None)
    assert is_auto_workdir_request("")
    assert not is_auto_workdir_request("kept")


def test_absolute_under_root_ok(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    target = root / "abs-ok"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))
    monkeypatch.delenv("ALLOW_UNRESTRICTED_WORKDIR", raising=False)

    resolved = resolve_confined_workdir(str(target))
    assert resolved == target.resolve()
    assert resolved.is_dir()


def test_unrestricted_allows_outside(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    root.mkdir()
    outside = tmp_path / "power-user"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))
    monkeypatch.setenv("ALLOW_UNRESTRICTED_WORKDIR", "true")

    assert unrestricted_workdir_allowed()
    resolved = resolve_confined_workdir(str(outside))
    assert resolved == outside.resolve()
    assert resolved.is_dir()


def test_get_workspaces_dir_xdg_fallback(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SWARM_WORKSPACES_DIR", raising=False)
    monkeypatch.delenv("WORKSPACES_DIR", raising=False)
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(tmp_path / "data"))
    assert get_workspaces_dir() == tmp_path / "data" / "workspaces"


def test_cli_fusion_support_resolve_workdir(tmp_path: Path, monkeypatch):
    from swarm.blueprints.common import cli_fusion_support as support

    root = tmp_path / "workspaces"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))
    monkeypatch.delenv("ALLOW_UNRESTRICTED_WORKDIR", raising=False)

    minted = support.resolve_workdir({})
    assert minted is not None
    assert Path(minted).is_relative_to(root.resolve())
    assert (Path(minted) / AUTO_RUN_MARKER).is_file()
    assert support.resolve_workdir({}, required=False) is None
    got = support.resolve_workdir({"workdir": "rel-ok"})
    assert Path(got).is_relative_to(root.resolve())

    with pytest.raises(WorkdirEscapeError):
        support.resolve_workdir({"cwd": str(tmp_path / "nope")})


def test_cleanup_run_workdir_deletes_auto(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))

    auto = resolve_confined_workdir(None, prune_stale=False)
    assert auto.is_dir()
    assert cleanup_run_workdir(auto) is True
    assert not auto.exists()


def test_cleanup_run_workdir_refuses_user_path(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))

    user = resolve_confined_workdir("user-project", prune_stale=False)
    (user / "keep.txt").write_text("important\n", encoding="utf-8")
    assert cleanup_run_workdir(user) is False
    assert user.is_dir()
    assert (user / "keep.txt").read_text(encoding="utf-8") == "important\n"


def test_cleanup_run_workdir_refuses_outside_root(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    root.mkdir()
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))

    outside = tmp_path / "outside-run"
    outside.mkdir()
    (outside / AUTO_RUN_MARKER).write_text("1\n", encoding="utf-8")
    assert cleanup_run_workdir(outside) is False
    assert outside.is_dir()


def test_cleanup_run_workdir_refuses_workspaces_root(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    root.mkdir()
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))
    (root / AUTO_RUN_MARKER).write_text("1\n", encoding="utf-8")

    assert cleanup_run_workdir(root) is False
    assert root.is_dir()


def test_cleanup_run_workdir_none_and_missing(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))
    assert cleanup_run_workdir(None) is False
    assert cleanup_run_workdir(root / "run-deadbeefcafe") is False


def test_cleanup_and_prune_keep_user_run_hex_without_marker(tmp_path: Path, monkeypatch):
    """A user dir named run-<12 hex> without AUTO_RUN_MARKER must survive."""
    root = tmp_path / "workspaces"
    root.mkdir()
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))

    user = root / "run-deadbeefcafe"
    user.mkdir()
    assert looks_like_auto_run_name(user.name)
    keep = user / "notes.txt"
    keep.write_text("user workspace\n", encoding="utf-8")
    old = time.time() - (10 * 86400)
    os.utime(user, (old, old))

    assert (user / AUTO_RUN_MARKER).is_file() is False
    assert cleanup_run_workdir(user) is False
    assert user.is_dir()
    assert keep.read_text(encoding="utf-8") == "user workspace\n"

    removed = prune_stale_run_workdirs(max_age_days=7, root=root.resolve())
    assert removed == 0
    assert user.is_dir()
    assert keep.read_text(encoding="utf-8") == "user workspace\n"
    assert not is_auto_run_workdir(user)


def test_prune_stale_run_workdirs(tmp_path: Path, monkeypatch):
    root = tmp_path / "workspaces"
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(root))

    stale = resolve_confined_workdir(None, prune_stale=False)
    fresh = resolve_confined_workdir(None, prune_stale=False)
    user = resolve_confined_workdir("keep-me", prune_stale=False)

    old = time.time() - (10 * 86400)
    os.utime(stale, (old, old))

    removed = prune_stale_run_workdirs(max_age_days=7, root=root.resolve())
    assert removed == 1
    assert not stale.exists()
    assert fresh.is_dir()
    assert user.is_dir()
