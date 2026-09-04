"""REQ-147: Discoverable keybinding tips & Grok-Bot search parity."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "App.tsx"
FLAGS_TS = REPO_ROOT / "webui" / "frontend" / "src" / "experimental" / "flags.ts"
CMD_PALETTE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "experimental" / "CommandPalette.tsx"
SIDEBAR_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"
SEARCH_PALETTE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "SearchPalette.tsx"


def test_app_binds_global_cmd_k_search():
    content = APP_TSX.read_text(encoding="utf-8")
    assert "e.key.toLowerCase() === 'k'" in content
    assert "setSearchOpen((prev) => !prev)" in content
    assert "window.addEventListener('keydown', onKey)" in content


def test_command_palette_demoted_and_no_collision():
    flags = FLAGS_TS.read_text(encoding="utf-8")
    # command_palette must default to false unless explicitly turned on
    assert "flag === 'command_palette'" in flags
    assert "raw === 'on' || raw === 'true'" in flags
    assert "return flag !== 'command_palette'" in flags

    cmd_palette = CMD_PALETTE_TSX.read_text(encoding="utf-8")
    # Must require shiftKey or not intercept bare ⌘K / Ctrl+K
    assert "e.shiftKey" in cmd_palette


def test_sidebar_alt_pins_and_tips():
    sidebar = SIDEBAR_TSX.read_text(encoding="utf-8")
    # Alt/⌥+1…9 navigation
    assert "event.altKey" in sidebar
    assert "/^[1-9]$/.test(event.key)" in sidebar
    assert "visiblePins[idx]" in sidebar

    # Hover shortcut badge on favourite tiles
    assert "os-fav-tile__shortcut" in sidebar

    # Search placeholder / affordance displays ⌘K / Ctrl+K
    assert "searchShortcutLabel" in sidebar
    assert "os-rail-search__kbd" in sidebar

    # Dismissible first-load tips
    assert "first-load-tips" in sidebar
    assert "swarm_keybinding_tips_dismissed" in sidebar


def test_search_palette_footer_tips():
    palette = SEARCH_PALETTE_TSX.read_text(encoding="utf-8")
    assert "os-search-palette__footer" in palette
    assert "os-search-tip" in palette
    assert "Navigate" in palette
    assert "Select" in palette
    assert "Close" in palette
    assert "os-search-palette__kbd" in palette
