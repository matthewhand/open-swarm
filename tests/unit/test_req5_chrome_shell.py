"""REQ-5 / REQ-5d chrome contracts: Django shell matches Chat; no leftover gutter."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "src" / "swarm" / "templates" / "base.html"
OPERATOR_CSS = REPO / "src" / "swarm" / "static" / "css" / "operator.css"
SHELL_CSS = REPO / "src" / "swarm" / "static" / "css" / "rest_mode_style.css"
LOGIN_HTML = REPO / "src" / "swarm" / "templates" / "account" / "login.html"
SIDEBAR_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"
THEME_JS = REPO / "src" / "swarm" / "static" / "js" / "chrome_theme.js"
SETTINGS_HTML = REPO / "src" / "swarm" / "templates" / "settings_dashboard.html"
TEAMS_ADMIN = REPO / "src" / "swarm" / "templates" / "teams_admin.html"
SESSIONS = REPO / "src" / "swarm" / "templates" / "session_explorer.html"
BLUEPRINTS = REPO / "src" / "swarm" / "templates" / "blueprint_library.html"
SPA_INDEX_HTML = REPO / "webui" / "frontend" / "index.html"
SPA_INDEX_CSS = REPO / "webui" / "frontend" / "src" / "index.css"
SPA_APP = REPO / "webui" / "frontend" / "src" / "App.tsx"


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


def test_login_flex_center_is_scoped_to_os_login():
    """Unscoped body { display:flex; justify-content:center } was the 35% void."""
    css = OPERATOR_CSS.read_text(encoding="utf-8")
    html = LOGIN_HTML.read_text(encoding="utf-8")
    assert 'class="os-login"' in html
    assert "body.os-login" in css
    assert re.search(r"(?m)^body\s*\{", css) is None
    assert re.search(r"(?m)^(?!body\.os-login\b)body\s*\{", css) is None


def test_operator_shell_is_column_chrome_matching_chat():
    css = SHELL_CSS.read_text(encoding="utf-8")
    html = BASE.read_text(encoding="utf-8")
    assert 'class="os-app"' in html
    assert 'class="os-header' in html
    assert 'class="os-shell"' in html
    assert re.search(r"body\.os-app\s*\{[^}]*flex-direction:\s*column", css, re.S)
    assert re.search(r"body\.os-app\s*\{[^}]*align-items:\s*stretch", css, re.S)
    assert re.search(r"\.os-header\s*\{[^}]*width:\s*100%", css, re.S)
    assert re.search(r"\.os-shell\s*\{[^}]*width:\s*100%", css, re.S)
    assert re.search(r"\.os-shell\s*\{[^}]*flex-direction:\s*row", css, re.S)
    assert ".os-agent-item__text" in css
    assert "min-width: 0" in css


def test_session_error_preview_wraps_instead_of_clipping():
    css = OPERATOR_CSS.read_text(encoding="utf-8")
    assert re.search(r"\.se-preview\s*\{[^}]*overflow-wrap:\s*anywhere", css, re.S)
    assert re.search(r"\.se-preview\s*\{[^}]*word-break:\s*break-word", css, re.S)


def test_spa_document_chrome_is_near_black():
    html = SPA_INDEX_HTML.read_text(encoding="utf-8")
    css = SPA_INDEX_CSS.read_text(encoding="utf-8")
    app = SPA_APP.read_text(encoding="utf-8")
    assert 'data-theme="dark"' in html
    assert "background-color: #0c0c0c" in css
    assert "dark --default" in css
    assert "applyDocumentTheme" in app
    assert "document.documentElement.setAttribute('data-theme'" in app
