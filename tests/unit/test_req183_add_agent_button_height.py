"""REQ-183: Add-agent + circle height <= Search pill (Fixes #639)."""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_CSS = REPO_ROOT / "webui" / "frontend" / "src" / "index.css"


def test_add_agent_button_height_matches_or_less_than_search_pill():
    css = INDEX_CSS.read_text(encoding="utf-8")

    # Verify .os-rail-search height
    search_pill_match = re.search(r"\.os-rail-search\s*\{[^}]*?height:\s*([^;]+);", css)
    assert search_pill_match, ".os-rail-search height rule must exist"
    search_pill_height = search_pill_match.group(1).strip()

    # Verify .os-search-add-btn height
    add_btn_match = re.search(r"\.os-search-add-btn\s*\{[^}]*?height:\s*([^;]+);", css)
    assert add_btn_match, ".os-search-add-btn height rule must exist"
    add_btn_height = add_btn_match.group(1).strip()

    # Both should be 2.25rem (36px)
    assert add_btn_height == search_pill_height == "2.25rem"

    # Verify touch target hit-area pseudo-element
    assert ".os-search-add-btn::before" in css
    before_match = re.search(r"\.os-search-add-btn::before\s*\{[^}]*?min-width:\s*([^;]+);", css)
    assert before_match
    assert before_match.group(1).strip() == "44px"
