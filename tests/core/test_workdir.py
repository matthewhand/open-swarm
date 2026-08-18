"""Tests for confined workdir resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.core.workdir import (
    WorkdirEscapeError,
    get_workspaces_dir,
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

    a = resolve_confined_workdir(None)
    b = resolve_confined_workdir("")
    assert a.is_dir() and b.is_dir()
    assert a != b
    assert a.is_relative_to(root.resolve())
    assert b.is_relative_to(root.resolve())
    assert a.name.startswith("run-")


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

    assert support.resolve_workdir({}) is None
    assert support.resolve_workdir({}, required=True).startswith(str(root.resolve()))
    got = support.resolve_workdir({"workdir": "rel-ok"})
    assert Path(got).is_relative_to(root.resolve())

    with pytest.raises(WorkdirEscapeError):
        support.resolve_workdir({"cwd": str(tmp_path / "nope")})
