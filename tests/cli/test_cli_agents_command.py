"""Tests for the `swarm-cli cli-agents` command (discovery + --json/--suggest)."""

from __future__ import annotations

import json
import logging
import sys

import pytest
from typer.testing import CliRunner

from swarm.core.swarm_cli import app

PY = sys.executable
runner = CliRunner(mix_stderr=False)  # keep logging (stderr) out of the JSON on stdout


@pytest.fixture(autouse=True)
def _quiet_logging():
    # CliRunner swaps and closes stdout/stderr around each invoke; pytest's live
    # log handlers then write to the closed stream ("I/O operation on closed
    # file"). Silence logging for the duration of these CLI invocations.
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)


def _write_config(tmp_path, cli_agents):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(
        json.dumps(
            {
                "llm": {"default": {"provider": "openai", "model": "gpt-4o", "api_key": "x"}},
                "cli_agents": cli_agents,
            }
        )
    )
    return str(cfg)


def test_json_empty_config_emits_empty_agents(tmp_path):
    cfg = _write_config(tmp_path, {})
    result = runner.invoke(app, ["cli-agents", "--json", "--config", cfg])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"agents": []}


def test_json_lists_configured_agents(tmp_path):
    cfg = _write_config(
        tmp_path,
        {"echo": {"cmd": [PY, "-c", "print(1)", "{prompt}"], "mode": "write"}},
    )
    result = runner.invoke(app, ["cli-agents", "--json", "--config", cfg])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [a["name"] for a in payload["agents"]] == ["echo"]
    assert payload["agents"][0]["installed"] is True  # python is on PATH
    assert payload["agents"][0]["mode"] == "write"


def test_json_suggest_includes_suggestions(tmp_path, monkeypatch):
    from swarm.core import cli_catalog

    monkeypatch.setattr(cli_catalog.shutil, "which", lambda exe: "/usr/bin/" + exe)
    cfg = _write_config(tmp_path, {})
    result = runner.invoke(app, ["cli-agents", "--json", "--suggest", "--config", cfg])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload["suggestions"]) == set(cli_catalog.catalog_names())


def test_init_prints_complete_config(monkeypatch):
    from swarm.core import cli_catalog

    monkeypatch.setattr(cli_catalog, "installed_catalog_clis", lambda: ["claude", "gemini"])
    result = runner.invoke(app, ["cli-agents", "--init"])
    assert result.exit_code == 0
    cfg = json.loads(result.stdout)
    assert set(cfg["cli_agents"]) == {"claude", "gemini"}
    assert "cli_fusion" in cfg and "cli_orchestrator" in cfg and "cli_map" in cfg


def test_init_write_creates_config_file(tmp_path, monkeypatch):
    from swarm.core import cli_catalog

    monkeypatch.setattr(cli_catalog, "installed_catalog_clis", lambda: ["claude"])
    dest = tmp_path / "swarm_config.json"
    result = runner.invoke(app, ["cli-agents", "--init", "--write", "--config", str(dest)])
    assert result.exit_code == 0
    assert dest.exists()
    cfg = json.loads(dest.read_text())
    assert "claude" in cfg["cli_agents"]
    # writing again backs up the existing file
    result2 = runner.invoke(app, ["cli-agents", "--init", "--write", "--config", str(dest)])
    assert result2.exit_code == 0
    assert (tmp_path / "swarm_config.json.bak").exists()


def test_short_flags_and_agents_alias(monkeypatch):
    from swarm.core import cli_catalog

    monkeypatch.setattr(cli_catalog, "installed_catalog_clis", lambda: ["grok"])
    # short -i works, and `agents` is an alias for `cli-agents`
    r1 = runner.invoke(app, ["cli-agents", "-i"])
    assert r1.exit_code == 0 and "cli_agents" in r1.stdout
    r2 = runner.invoke(app, ["agents", "-i"])
    assert r2.exit_code == 0 and json.loads(r2.stdout)["cli_agents"]


def test_table_output_without_json(tmp_path):
    cfg = _write_config(
        tmp_path, {"echo": {"cmd": [PY, "-c", "print(1)", "{prompt}"]}}
    )
    result = runner.invoke(app, ["cli-agents", "--config", cfg])
    assert result.exit_code == 0
    assert "AGENT" in result.stdout and "echo" in result.stdout
    assert "1/1 configured CLI agents installed" in result.stdout
