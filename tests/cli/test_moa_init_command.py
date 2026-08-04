"""Tests for swarm-cli moa-init."""

from __future__ import annotations

import json
from pathlib import Path

from tests.xdg_isolation import run_swarm_cli


def test_moa_init_write(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    proc = run_swarm_cli(
        "moa-init",
        "--config",
        str(cfg),
        "--write",
        "--backend",
        "fake",
        "-p",
        "a,b",
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["moa"]["backend"] == "fake"
    assert data["moa"]["participants"] == ["a", "b"]


def test_moa_init_show_openwebui(tmp_path: Path):
    proc = run_swarm_cli(
        "moa-init",
        "--show-openwebui",
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["model"] == "moa"
