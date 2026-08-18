"""Regression: creator status toasts must escape untrusted message text.

showTeamMessage / showMessage previously interpolated `message` into innerHTML.
Call sites pass swarm names, server errors, and paths — a DOM XSS vector.

Agent Creator Pro static JS was deleted (route redirects to `/agent-creator/`);
XSS coverage for creators is the live team + agent creator templates.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEAM_CREATOR = ROOT / "src" / "swarm" / "templates" / "team_creator.html"
AGENT_CREATOR = ROOT / "src" / "swarm" / "templates" / "agent_creator.html"


def _slice_after(source: str, marker: str, length: int = 900) -> str:
    idx = source.find(marker)
    assert idx != -1, f"marker not found: {marker}"
    return source[idx : idx + length]


def test_team_creator_show_team_message_escapes_message():
    source = TEAM_CREATOR.read_text(encoding="utf-8")
    body = _slice_after(source, "function showTeamMessage")
    assert "escapeHtml(message)" in body
    assert re.search(r"\$\{\s*message\s*\}", body) is None
    assert "function escapeHtml" in source


def test_agent_creator_show_message_escapes_message():
    source = AGENT_CREATOR.read_text(encoding="utf-8")
    body = _slice_after(source, "function showMessage")
    assert "escapeHtml(message)" in body
    assert re.search(r"\$\{\s*message\s*\}", body) is None
