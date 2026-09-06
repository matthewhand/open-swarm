"""CLI smoke for ``swarm-cli tui`` Wave 0 scaffold (REQ-111)."""

from __future__ import annotations

import json
import re

from typer.testing import CliRunner

from swarm.core.swarm_cli import app
from swarm.tui.client import RailSeat, SwarmApiError

runner = CliRunner(mix_stderr=False)

# Rich/Click help can color each hyphen, so "--once" is not contiguous in raw stdout.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mK]")


def test_tui_help_lists_command():
    result = runner.invoke(app, ["tui", "--help"])
    assert result.exit_code == 0
    stdout = _ANSI_RE.sub("", result.stdout)
    assert "same HTTP API" in stdout or "REQ-111" in stdout
    assert "--once" in stdout
    assert "--interactive" in stdout
    assert "--base-url" in stdout


def test_tui_once_renders_rail_and_placeholder(monkeypatch):
    monkeypatch.setattr(
        "swarm.tui.cli.list_rail_agents",
        lambda **_: [
            RailSeat(id="support", name="Support", kind="api", source="blueprints"),
            RailSeat(id="grok", name="Grok", kind="cli", source="cli-agents"),
        ],
    )
    result = runner.invoke(app, ["tui", "--once", "--base-url", "http://127.0.0.1:8000"])
    assert result.exit_code == 0, result.stderr
    assert "AGENTS" in result.stdout
    assert "Support" in result.stdout
    assert "Grok" in result.stdout
    assert "placeholder" in result.stdout.lower()
    assert "Wave 0" in result.stdout
    assert "8001" not in result.stdout


def test_tui_json_lists_seats_and_kind_sections(monkeypatch):
    monkeypatch.setattr(
        "swarm.tui.cli.list_rail_agents",
        lambda **_: [
            RailSeat(id="support", name="Support", kind="api", source="blueprints"),
            RailSeat(id="grok", name="Grok", kind="cli", source="cli-agents"),
            RailSeat(id="team:office", name="Office", kind="team", source="team-rosters"),
        ],
    )
    result = runner.invoke(app, ["tui", "--json"])
    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["object"] == "tui.rail"
    assert [row["id"] for row in payload["data"]] == ["support", "grok", "team:office"]
    # Wave 1b: sections bucket seat ids by kind, empty sections omitted.
    assert payload["sections"] == {
        "CLI": ["grok"],
        "API": ["support"],
        "Blueprint": ["team:office"],
    }


def test_tui_api_down_is_honest(monkeypatch):
    monkeypatch.setattr(
        "swarm.tui.cli.list_rail_agents",
        lambda **_: (_ for _ in ()).throw(SwarmApiError("API unreachable at http://127.0.0.1:8000")),
    )
    result = runner.invoke(app, ["tui", "--once"])
    assert result.exit_code == 1
    assert "API unreachable" in result.stderr
    assert "Support" not in result.stdout


def test_tui_interactive_default_needs_terminal():
    # Wave 1a: interactive is the default, but a non-TTY (CI / pipe) must get
    # an honest hint instead of hanging or pretending to open a TUI.
    result = runner.invoke(app, ["tui"])
    assert result.exit_code == 2
    assert "--once" in result.stderr
    assert "terminal" in result.stderr

