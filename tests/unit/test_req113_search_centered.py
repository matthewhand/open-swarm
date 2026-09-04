"""REQ-113: Search popup — centered and larger."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_CSS = REPO_ROOT / "webui" / "frontend" / "src" / "index.css"
SEARCH_PALETTE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "SearchPalette.tsx"


def test_index_css_search_overlay_centered():
    css = INDEX_CSS.read_text(encoding="utf-8")
    assert ".os-search-overlay" in css
    # Horizontally and vertically centered modal overlay
    assert "justify-content: center;" in css
    assert "align-items: center;" in css


def test_index_css_search_palette_enlarged():
    css = INDEX_CSS.read_text(encoding="utf-8")
    assert ".os-search-palette" in css
    # Roomy sizing: ~min(560px, 90vw / calc(100vw - 2rem))
    assert "560px" in css
    assert "max-height" in css


def test_search_palette_component_has_centered_classes():
    tsx = SEARCH_PALETTE_TSX.read_text(encoding="utf-8")
    assert "os-search-overlay--centered" in tsx
    assert "os-search-palette--centered" in tsx
    assert "os-search-palette--large" in tsx
