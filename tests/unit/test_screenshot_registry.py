"""Screenshot tour registry consistency (USERGUIDE / GUIDED_TOUR honesty).

Drives real files in the repo: every PNG embedded by tour docs must exist,
and every stem in scripts/capture_user_journey.PAGES must be listed in
docs/SCREENSHOTS.md.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCREENSHOTS_DIR = REPO / "docs" / "screenshots"
SCREENSHOTS_MD = REPO / "docs" / "SCREENSHOTS.md"
GUIDED_TOUR = REPO / "docs" / "GUIDED_TOUR.md"
USER_JOURNEY = REPO / "docs" / "USER_JOURNEY.md"
CAPTURE_SCRIPT = REPO / "scripts" / "capture_user_journey.py"


def _png_embeds(md_text: str) -> set[str]:
    """Return basenames referenced as ./screenshots/<file>.png or screenshots/…"""
    found = set()
    for m in re.finditer(
        r"(?:\./)?screenshots/(?:mobile/)?([a-z0-9_-]+\.png)",
        md_text,
        re.I,
    ):
        found.add(m.group(1))
    return found


def _capture_script_stems() -> list[str]:
    """Parse PAGES list from capture_user_journey.py without reimplementing it."""
    src = CAPTURE_SCRIPT.read_text()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "PAGES":
                    pages = ast.literal_eval(node.value)
                    return [row[0] for row in pages]
    raise AssertionError("PAGES list not found in capture_user_journey.py")


def test_guided_tour_and_journey_embeds_exist_on_disk():
    embeds = _png_embeds(GUIDED_TOUR.read_text()) | _png_embeds(USER_JOURNEY.read_text())
    assert embeds, "tour docs should embed at least one screenshot"
    missing = []
    for name in sorted(embeds):
        desktop = SCREENSHOTS_DIR / name
        # embeds may be mobile/foo.png basename only — check desktop registry
        if not desktop.is_file():
            # allow only mobile path references if present under mobile/
            mobile = SCREENSHOTS_DIR / "mobile" / name
            if not mobile.is_file():
                missing.append(name)
    assert not missing, f"PNG embeds missing from docs/screenshots/: {missing}"


def test_capture_pages_covered_by_registry():
    stems = _capture_script_stems()
    registry = SCREENSHOTS_MD.read_text()
    missing = [s for s in stems if f"`{s}.png`" not in registry and f"{s}.png" not in registry]
    assert not missing, f"capture stems missing from SCREENSHOTS.md: {missing}"


def test_capture_pages_png_files_exist_desktop_and_mobile():
    stems = _capture_script_stems()
    missing = []
    for s in stems:
        if not (SCREENSHOTS_DIR / f"{s}.png").is_file():
            missing.append(f"desktop:{s}.png")
        if not (SCREENSHOTS_DIR / "mobile" / f"{s}.png").is_file():
            missing.append(f"mobile:{s}.png")
    assert not missing, f"capture outputs missing: {missing}"


def test_registry_does_not_claim_spa_dual_product_for_redirects():
    """Docs must not describe bare /teams as a separate SPA product."""
    tour = GUIDED_TOUR.read_text()
    # Honest redirect language expected.
    assert "redirect" in tour.lower()
    assert "/teams/launch/" in tour
    # Old dual-product phrasing should be gone.
    assert "Team management, wired to the JSON Teams API" not in tour
    assert "API-token form, read-only server settings by category" not in tour


def test_userguide_points_to_visual_tour_and_django_operator_truth():
    ug = (REPO / "USERGUIDE.md").read_text()
    assert "GUIDED_TOUR.md" in ug
    assert "SCREENSHOTS.md" in ug
    assert "Django" in ug
    assert "redirect" in ug.lower() or "trailing-slash" in ug or "trailing slash" in ug


def test_capture_script_parks_django_and_spa_mobile_bottom_navs():
    """Full-page stitch must not leave fixed SPA/Django bars painting over content."""
    src = CAPTURE_SCRIPT.read_text()
    assert ".os-bottom-nav" in src
    assert "fixed.bottom-0" in src or "bottom-0" in src
    assert "position = 'static'" in src or 'position = "static"' in src or "position='static'" in src


def test_user_journey_launcher_caption_matches_hybrid_team_default():
    """teams-launch capture defaults to first option hybrid_team, not django_chat."""
    text = USER_JOURNEY.read_text()
    assert "hybrid_team" in text
    # Must not claim django_chat is pre-selected in the capture.
    assert "django_chat` is pre-selected" not in text
    assert "django_chat is pre-selected" not in text


def test_user_journey_screenshot_date_is_current_regeneration():
    text = USER_JOURNEY.read_text()
    assert "2026-07-21" in text
    assert "2026-06-11 with a fresh development database" not in text
