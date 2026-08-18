"""Tests for swarm-cli config init."""

from __future__ import annotations

import json
from pathlib import Path

from tests.xdg_isolation import run_swarm_cli


def test_config_init_writes_default(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    proc = run_swarm_cli(
        "config",
        "init",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert cfg.is_file()
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "llm" in data
    assert "default" in data["llm"]
    assert "Wrote default config" in proc.stdout


def test_config_init_refuses_overwrite_without_force(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {"keep": {"model": "x"}}}), encoding="utf-8")
    proc = run_swarm_cli(
        "config",
        "init",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 1
    assert "already exists" in (proc.stderr + proc.stdout).lower()
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "keep" in data["llm"]


def test_config_init_force_overwrites(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {"keep": {"model": "x"}}}), encoding="utf-8")
    proc = run_swarm_cli(
        "config",
        "init",
        "--force",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "default" in data["llm"]
    assert "keep" not in data["llm"]


def test_config_remove_missing_exits_nonzero(tmp_path: Path):
    """Missing profile must exit 1 (not print-and-succeed)."""
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {"default": {"model": "x"}}, "mcpServers": {}}), encoding="utf-8")
    proc = run_swarm_cli(
        "config",
        "remove",
        "--section",
        "llm",
        "--name",
        "does_not_exist",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 1
    combined = (proc.stderr + proc.stdout).lower()
    assert "not found" in combined
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "default" in data["llm"]


def test_config_remove_existing_persists(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(
        json.dumps({"llm": {"default": {"model": "x"}, "temp": {"model": "y"}}, "mcpServers": {}}),
        encoding="utf-8",
    )
    proc = run_swarm_cli(
        "config",
        "remove",
        "--section",
        "llm",
        "--name",
        "temp",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Removed 'temp'" in proc.stdout
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "temp" not in data["llm"]
    assert "default" in data["llm"]
