"""CLI blueprint name must stay a single segment under library/bin roots."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from swarm.core import paths
from swarm.core.swarm_cli import (
    _path_is_under_root,
    _require_safe_blueprint_segment,
    _safe_blueprint_segment,
    add_cmd,
    delete_cmd,
    uninstall_cmd,
)


@pytest.mark.parametrize(
    "name",
    [
        "../outside",
        "../../etc/passwd",
        "foo/bar",
        "foo\\bar",
        "/tmp/abs",
        "..",
        ".",
        "",
        "  ",
        "name\x00evil",
    ],
)
def test_safe_blueprint_segment_rejects_traversal(name: str):
    assert _safe_blueprint_segment(name) is None
    with pytest.raises(typer.Exit) as exc:
        _require_safe_blueprint_segment(name)
    assert exc.value.exit_code == 1


@pytest.mark.parametrize("name", ["good_bp", "Agent-1", "my.blueprint"])
def test_safe_blueprint_segment_accepts_simple_names(name: str):
    assert _safe_blueprint_segment(name) == name
    assert _require_safe_blueprint_segment(name) == name


def test_delete_rejects_path_traversal_and_does_not_rmtree_outside(tmp_path, monkeypatch):
    """``swarm-cli delete ../…/victim`` must not delete outside the library."""
    data_dir = tmp_path / "swarm_data"
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(data_dir))
    bp_root = paths.get_user_blueprints_dir()
    bp_root.mkdir(parents=True)

    victim = tmp_path / "victim_dir"
    victim.mkdir()
    marker = victim / "keep.txt"
    marker.write_text("untouched", encoding="utf-8")

    # Climb from blueprints/ out to tmp_path/victim_dir (depth depends on XDG layout).
    evil = str(Path(*([".."] * len(bp_root.resolve().relative_to(tmp_path).parts))) / "victim_dir")
    evil_dest = (bp_root / evil).resolve()
    assert evil_dest == victim.resolve()
    assert not _path_is_under_root(evil_dest, bp_root)

    with pytest.raises(typer.Exit) as exc:
        delete_cmd(evil)
    assert exc.value.exit_code == 1
    assert marker.read_text(encoding="utf-8") == "untouched"
    assert victim.is_dir()
    assert list(bp_root.iterdir()) == []


def test_delete_removes_only_under_library(tmp_path, monkeypatch):
    data_dir = tmp_path / "swarm_data"
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(data_dir))
    bp_root = paths.get_user_blueprints_dir()
    target = bp_root / "doomed_bp"
    target.mkdir(parents=True)
    (target / "blueprint.py").write_text("x=1\n", encoding="utf-8")

    delete_cmd("doomed_bp")
    assert not target.exists()
    assert bp_root.is_dir()


def test_add_rejects_traversal_name(tmp_path, monkeypatch):
    data_dir = tmp_path / "swarm_data"
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(data_dir))
    src = tmp_path / "src_bp"
    src.mkdir()
    (src / "blueprint.py").write_text("x=1\n", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(typer.Exit) as exc:
        add_cmd(str(src), name="../../../outside/pwned")
    assert exc.value.exit_code == 1
    assert list(outside.iterdir()) == []
    assert not (paths.get_user_blueprints_dir() / "pwned").exists()


def test_add_copies_under_xdg_blueprints(tmp_path, monkeypatch):
    data_dir = tmp_path / "swarm_data"
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(data_dir))
    src = tmp_path / "src_bp"
    src.mkdir()
    (src / "blueprint.py").write_text("print('hi')\n", encoding="utf-8")

    add_cmd(str(src), name="good_add")
    dest = paths.get_user_blueprints_dir() / "good_add" / "blueprint.py"
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == "print('hi')\n"
    assert _path_is_under_root(dest, paths.get_user_blueprints_dir())


def test_uninstall_rejects_path_traversal(tmp_path, monkeypatch):
    data_dir = tmp_path / "swarm_data"
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(data_dir))
    bin_dir = paths.get_user_bin_dir()
    bin_dir.mkdir(parents=True)

    victim = tmp_path / "victim_bin"
    victim.write_text("keep", encoding="utf-8")
    evil = str(Path(*([".."] * len(bin_dir.resolve().relative_to(tmp_path).parts))) / "victim_bin")
    assert (bin_dir / evil).resolve() == victim.resolve()

    with pytest.raises(typer.Exit) as exc:
        uninstall_cmd(evil)
    assert exc.value.exit_code == 1
    assert victim.read_text(encoding="utf-8") == "keep"
