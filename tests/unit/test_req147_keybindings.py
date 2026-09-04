"""REQ-147: Discoverable keybinding tips & Grok-Bot search parity."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "App.tsx"
FLAGS_TS = REPO_ROOT / "webui" / "frontend" / "src" / "experimental" / "flags.ts"
CMD_PALETTE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "experimental" / "CommandPalette.tsx"
SIDEBAR_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"
SEARCH_PALETTE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "SearchPalette.tsx"
CHAT_PAGE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"
KEYBINDING_TIPS_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "KeybindingTips.tsx"
KEYBINDING_TIPS_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "keybindingTips.ts"


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

    # Search placeholder / affordance displays ⌘K / Ctrl+K (do not drop Search parity)
    assert "searchShortcutLabel" in sidebar
    assert "os-rail-search__kbd" in sidebar
    assert "first-load-tips" not in sidebar
    assert "os-keybinding-tips alert" not in sidebar


def test_search_palette_footer_tips():
    palette = SEARCH_PALETTE_TSX.read_text(encoding="utf-8")
    assert "os-search-palette__footer" in palette
    assert "os-search-tip" in palette
    assert "Navigate" in palette
    assert "Select" in palette
    assert "Close" in palette
    assert "os-search-palette__kbd" in palette


def test_first_load_tips_under_composer():
    chat = CHAT_PAGE_TSX.read_text(encoding="utf-8")
    tips = KEYBINDING_TIPS_TSX.read_text(encoding="utf-8")
    persist = KEYBINDING_TIPS_TS.read_text(encoding="utf-8")

    assert "KeybindingTips" in chat
    assert "composer-send-hint" in chat
    assert "first-load-tips" in tips
    assert "Search" in tips
    assert "Pins" in tips
    assert "Clear" in tips
    assert "swarm_keybinding_tips_dismissed" in persist
    assert 'className="os-keybinding-tips"' in tips
    assert "os-keybinding-tips alert" not in tips
