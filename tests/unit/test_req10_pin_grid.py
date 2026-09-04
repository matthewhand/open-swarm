"""REQ-10 unlabeled chrome pin grid: Django shell contracts."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "src" / "swarm" / "templates" / "base.html"
SIDEBAR_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"
PIN_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_pin_grid.js"
CSS = REPO / "src" / "swarm" / "static" / "css" / "rest_mode_style.css"


def test_base_shell_has_unlabeled_pin_grid_not_favourites_heading():
    html = BASE.read_text(encoding="utf-8")
    assert 'id="os-agent-pin-grid"' in html
    assert 'aria-label="Pinned agents"' in html
    assert "agent_pin_grid.js" in html
    assert "Favourites" not in html
    assert "Favorites" not in html


def test_sidebar_excludes_pinned_ids_from_the_list():
    js = SIDEBAR_JS.read_text(encoding="utf-8")
    assert "swarm_pinned_agents" in js
    assert "pinnedIds" in js
    assert "loadPinnedIds" in js


def test_pin_grid_js_persists_and_can_remove_one():
    js = PIN_JS.read_text(encoding="utf-8")
    assert "swarm_pinned_agents" in js
    assert "localStorage.setItem" in js
    assert "os-agent-tile" in js
    assert "Remove " in js
    assert "/chat?blueprint=" in js
    assert "Favourites" not in js
    assert "hide-all" not in js.lower()


def test_pin_grid_css_is_unlabeled_chrome_strip():
    css = CSS.read_text(encoding="utf-8")
    assert ".os-agent-pin-grid" in css
    assert ".os-agent-tile" in css
    assert "Favourites" not in css
