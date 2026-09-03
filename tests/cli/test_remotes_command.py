"""CLI tests for swarm-cli remotes."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from swarm.core.remotes import HealthResult, RemoteSpec
from tests.xdg_isolation import run_swarm_cli


def test_remotes_list(tmp_path: Path):
    proc = run_swarm_cli("remotes", "list", xdg_root=tmp_path / "xdg", timeout=30)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "hermes" in proc.stdout
    assert "omb" in proc.stdout
    assert "rakazo" in proc.stdout
    assert "swarm" in proc.stdout


def test_remotes_set_persists(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {"default": {"model": "x"}}}), encoding="utf-8")
    proc = run_swarm_cli(
        "remotes",
        "set",
        "hermes",
        "--base-url",
        "http://10.0.0.36:8642",
        "--api-key-env",
        "HERMES_API_KEY",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["remotes"]["hermes"]["base_url"] == "http://10.0.0.36:8642"
    assert data["remotes"]["hermes"]["api_key"] == "${HERMES_API_KEY}"
    assert "Persisted" in proc.stdout


def test_remotes_set_refuses_fly(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {}}), encoding="utf-8")
    proc = run_swarm_cli(
        "remotes",
        "set",
        "omb",
        "--base-url",
        "https://open-litellm.fly.dev/v1",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 1
    assert "open-litellm" in (proc.stderr + proc.stdout).lower()


def test_remotes_health_uses_core(tmp_path: Path):
    fake = HealthResult(remote="hermes", ok=False, state="DOWN", detail="tcp timeout")
    from typer.testing import CliRunner

    from swarm.core.swarm_cli import app

    runner = CliRunner()
    with patch("swarm.core.remotes.check_health", return_value=fake):
        result = runner.invoke(app, ["remotes", "health", "hermes"])
    assert result.exit_code == 1
    assert "DOWN" in result.stdout
    assert "hermes" in result.stdout


def test_remotes_place_unplace_team(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {}}), encoding="utf-8")
    proc = run_swarm_cli(
        "remotes",
        "unplace",
        "omb",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["agent_team"]["members"] == ["hermes", "rakazo"]
    assert "Persisted agent_team.members" in proc.stdout

    proc = run_swarm_cli(
        "remotes",
        "place",
        "omb",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "omb" in data["agent_team"]["members"]

    proc = run_swarm_cli("remotes", "team", xdg_root=tmp_path / "xdg", timeout=30)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["object"] == "agent_team"
    assert "not_teams_page" in payload["vocabulary"]


def test_remotes_get_json(tmp_path: Path):
    from typer.testing import CliRunner

    from swarm.core.swarm_cli import app

    runner = CliRunner()
    spec = RemoteSpec(
        id="rakazo",
        title="Rakazo",
        host_label="Windows2",
        base_url="http://10.0.0.32:3100",
        ui_url="http://10.0.0.32:5173",
        source="default",
    )
    with patch("swarm.core.remotes.load_remote", return_value=spec):
        result = runner.invoke(app, ["remotes", "get", "rakazo"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["base_url"] == "http://10.0.0.32:3100"
    assert payload["api_key_set"] is False


def test_remotes_set_swarm_stub(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {}}), encoding="utf-8")
    proc = run_swarm_cli(
        "remotes",
        "set",
        "swarm",
        "--base-url",
        "http://127.0.0.1:9",
        "--api-key-env",
        "CHANGE_ME",
        "--config",
        str(cfg),
        xdg_root=tmp_path / "xdg",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["remotes"]["swarm"]["base_url"] == "http://127.0.0.1:9"
    assert data["remotes"]["swarm"]["api_key"] == "${CHANGE_ME}"
