"""REQ-21 contracts: CLI shape, docs honesty, no Neon, mock-only CI."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLIENT = REPO / "src" / "swarm" / "herdr" / "client.py"
DOCS = REPO / "docs" / "HERDR.md"
SIDEBAR = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"
SETTINGS = REPO / "src" / "swarm" / "templates" / "settings_dashboard.html"
TEAMS = REPO / "src" / "swarm" / "templates" / "teams_admin.html"
SETTINGS_PY = REPO / "src" / "swarm" / "settings.py"


def test_client_uses_official_herdr_argv_only():
    src = CLIENT.read_text(encoding="utf-8")
    assert "agent prompt" in src
    assert "workspace" in src and "list" in src
    assert "wait-until" in src or "agent wait" in src
    assert "--remote" in src
    # Do not invent a socket protocol.
    assert "AF_UNIX" not in src
    assert "HERDR_SOCKET_PATH" not in src
    assert "agent_prompted" in src


def test_docs_are_not_hermes_omb_rakazo_and_same_host_default():
    text = DOCS.read_text(encoding="utf-8")
    assert "NOT Hermes" in text or "not Hermes" in text
    assert "OMB" in text
    assert "Rakazo" in text
    assert "localhost" in text
    assert "--remote" in text
    assert "agent_prompted" in text
    assert "HERDR_PING_OK" in text
    assert "w3:p1" in text
    assert "mock" in text.lower()
    assert "WORKING" in text or "working" in text
    assert "Neon" in text or "DATABASE_URL" in text


def test_sidepane_and_teams_can_pick_herdr_members():
    sidebar = SIDEBAR.read_text(encoding="utf-8")
    assert "/v1/herdr-agents/" in sidebar
    assert "kind" in sidebar
    assert "herdr" in sidebar
    teams = TEAMS.read_text(encoding="utf-8")
    assert "herdr-members" in teams
    assert "kind=herdr" in teams
    settings = SETTINGS.read_text(encoding="utf-8")
    assert "kind=herdr" in settings
    assert "discover-herdr-agents" in settings
    assert "Add Herdr remote" in settings
    assert "OpenMousBot" in settings


def test_sqlite_default_unchanged_no_neon_url():
    src = SETTINGS_PY.read_text(encoding="utf-8")
    helper = (REPO / "src" / "swarm" / "core" / "database_config.py").read_text(
        encoding="utf-8"
    )
    assert "django.db.backends.sqlite3" in src or "django.db.backends.sqlite3" in helper
    # Feature must not hard-code Neon as a default host.
    assert "neon.tech" not in src.lower()
    assert "neon.tech" not in helper.lower()
