"""REQ-5c chrome contracts: Django shell + leftover rainbow CSS gone."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "src" / "swarm" / "templates" / "base.html"
OPERATOR_CSS = REPO / "src" / "swarm" / "static" / "css" / "operator.css"
SIDEBAR_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"
THEME_JS = REPO / "src" / "swarm" / "static" / "js" / "chrome_theme.js"
SETTINGS_HTML = REPO / "src" / "swarm" / "templates" / "settings_dashboard.html"
TEAMS_ADMIN = REPO / "src" / "swarm" / "templates" / "teams_admin.html"
SESSIONS = REPO / "src" / "swarm" / "templates" / "session_explorer.html"
BLUEPRINTS = REPO / "src" / "swarm" / "templates" / "blueprint_library.html"


def test_base_shell_has_home_matching_nav_and_agents_pane():
    html = BASE.read_text(encoding="utf-8")
    for label in ("Home", "Chat", "Blueprints", "Teams", "Sessions", "Settings"):
        assert f">{label}</a>" in html or f">{label}</button>" in html
    assert 'id="os-agent-sidebar"' in html
    assert 'aria-label="Agent list"' in html
    assert 'id="os-theme-toggle"' in html
    assert "agent_sidebar.js" in html
    assert "chrome_theme.js" in html
    assert "Hide from sidebar" not in html  # menu is created in JS, not a hide-all control


def test_settings_header_is_not_purple_gradient():
    css = OPERATOR_CSS.read_text(encoding="utf-8")
    assert "#667eea" not in css
    assert "#764ba2" not in css
    assert ".dashboard-header-card" in css
    assert "var(--os-panel)" in css


def test_agent_sidebar_js_hides_and_persists():
    js = SIDEBAR_JS.read_text(encoding="utf-8")
    assert "swarm_hidden_agents" in js
    assert "Hide from sidebar" in js
    assert "Unhide" in js
    assert "localStorage.setItem" in js
    assert "/v1/blueprints/" in js
    assert "no hide-all" in js


def test_theme_js_shares_spa_storage_key():
    js = THEME_JS.read_text(encoding="utf-8")
    assert "swarm_theme" in js
    assert "Switch to light theme" in js
    assert "Switch to dark theme" in js


def test_operator_pages_use_large_action_cards():
    for path in (SETTINGS_HTML, TEAMS_ADMIN, SESSIONS, BLUEPRINTS):
        html = path.read_text(encoding="utf-8")
        assert "os-action-card" in html, f"{path.name} missing large action cards"
        assert "os-action-card__title" in html


def test_teams_empty_state_is_honest_zero():
    html = TEAMS_ADMIN.read_text(encoding="utf-8")
    assert "0 teams registered" in html
    assert "Launch your first team" in html
