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


def _non_archive_screenshot_pngs() -> list[Path]:
    """Every PNG under docs/screenshots/ except intentional archive/."""
    return sorted(
        p
        for p in SCREENSHOTS_DIR.rglob("*.png")
        if "archive" not in p.relative_to(SCREENSHOTS_DIR).parts
    )


def _registry_rel(path: Path) -> str:
    return path.relative_to(SCREENSHOTS_DIR).as_posix()


def _docs_png_embed_targets() -> set[str]:
    """Relative paths under docs/screenshots/ that markdown under docs/ (+ README) embeds."""
    embed_re = re.compile(r"!\[[^\]]*\]\(([^)]+\.png)\)")
    found: set[str] = set()
    md_files = list((REPO / "docs").rglob("*.md")) + [REPO / "README.md"]
    for path in md_files:
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        for m in embed_re.finditer(text):
            rel = m.group(1)
            if rel.startswith("http"):
                continue
            target = (path.parent / rel).resolve()
            try:
                found.add(target.relative_to(SCREENSHOTS_DIR.resolve()).as_posix())
            except ValueError:
                continue
    return found


def _ast_str(node: ast.AST) -> str | None:
    """Constant string, or the literal prefix of an f-string / JoinedStr."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        # Path may be f"/sessions/{SESSION_DETAIL_ID}/" — stem is still plain.
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                break
        return "".join(parts) if parts else None
    return None


def _capture_script_stems() -> list[str]:
    """Parse PAGES list from capture_user_journey.py without reimplementing it.

    Rows may use f-strings for the path (e.g. session-detail); only the stem
    (tuple element 0) must be a plain string constant.
    """
    src = CAPTURE_SCRIPT.read_text()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "PAGES":
                    if not isinstance(node.value, ast.List):
                        raise AssertionError("PAGES must be a list literal")
                    stems: list[str] = []
                    for elt in node.value.elts:
                        if not isinstance(elt, ast.Tuple) or not elt.elts:
                            raise AssertionError(f"PAGES row must be a tuple: {ast.dump(elt)}")
                        stem = _ast_str(elt.elts[0])
                        if stem is None:
                            raise AssertionError(
                                f"PAGES stem must be a string constant: {ast.dump(elt.elts[0])}"
                            )
                        stems.append(stem)
                    return stems
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


def test_capture_script_injects_redirect_banner_for_spa_stems():
    """spa-* captures must be distinct from canonical pages (redirect banner)."""
    src = CAPTURE_SCRIPT.read_text()
    assert "os-capture-redirect-banner" in src
    assert "Redirected:" in src
    assert "urlparse" in src


def test_user_journey_embeds_sessions_and_profiles_when_captured():
    """If PAGES captures exist on disk, USER_JOURNEY must embed them (not link-only)."""
    text = USER_JOURNEY.read_text()
    embeds = _png_embeds(text)
    for stem in ("sessions", "session-detail", "profiles"):
        if (SCREENSHOTS_DIR / f"{stem}.png").is_file():
            assert f"{stem}.png" in embeds, (
                f"USER_JOURNEY.md must embed screenshots/{stem}.png when the "
                "capture exists (do not leave a GUIDED_TOUR-only pointer)"
            )


def test_guided_tour_embeds_session_detail_when_captured():
    """GUIDED_TOUR must embed session-detail.png when the journey capture exists."""
    if not (SCREENSHOTS_DIR / "session-detail.png").is_file():
        pytest.skip("session-detail.png not captured yet")
    text = GUIDED_TOUR.read_text()
    embeds = _png_embeds(text)
    assert "session-detail.png" in embeds, (
        "GUIDED_TOUR.md must embed screenshots/session-detail.png when captured"
    )


def test_session_detail_caption_is_seeded_fixture_not_live_run():
    """Tour captions must not claim session-detail.png is a live hybrid_team run."""
    for path in (GUIDED_TOUR, USER_JOURNEY):
        text = path.read_text().lower()
        # Require honest seeded-fixture language near the embed.
        assert "session-detail.png" in path.read_text()
        assert "seeded" in text
        assert "resp_journey_seed" in path.read_text()
        # Must not claim the PNG is evidence of a live multi-model / hybrid_team run.
        for banned in (
            "live hybrid_team run",
            "from a live hybrid_team",
            "live post /v1/responses run",
        ):
            assert banned not in text, f"{path.name} must not claim: {banned!r}"


def test_user_journey_launcher_caption_matches_hybrid_team_default():
    """teams-launch capture defaults to first option hybrid_team, not django_chat/fs_introspect."""
    for path in (USER_JOURNEY, GUIDED_TOUR, SCREENSHOTS_MD):
        text = path.read_text()
        # Near the launcher capture, docs must name the selected blueprint honestly.
        assert "hybrid_team" in text
        # Must not claim a different blueprint is pre-selected in the PNG.
        assert "django_chat` is pre-selected" not in text
        assert "django_chat is pre-selected" not in text
        assert "`fs_introspect`** selected" not in text
        assert "**`fs_introspect`** selected" not in text


def test_user_journey_screenshot_date_is_current_regeneration():
    text = USER_JOURNEY.read_text()
    assert "2026-08-18" in text
    assert "2026-06-11 with a fresh development database" not in text
    assert "2026-07-21" not in text


def test_tour_captions_include_spa_desktop_chat_nav():
    """landing.png / App.tsx desktop top nav includes Chat after ADR-001."""
    needle_spaced = "Home · Chat · Blueprints · Teams · Sessions · Settings"
    needle_tight = "Home·Chat·Blueprints·Teams·Sessions·Settings"
    for path in (GUIDED_TOUR, USER_JOURNEY, SCREENSHOTS_MD):
        # Collapse wrapping newlines inside the bold nav phrase.
        flat = " ".join(path.read_text().split())
        assert needle_spaced in flat or needle_tight in flat, (
            f"{path.name} must name SPA desktop Chat in the top-nav caption"
        )


def test_tour_captions_do_not_claim_sticky_banner_in_checked_in_spa_pngs():
    """Checked-in spa-*.png are redirect landings; banner is injection-on-regen only."""
    for path in (GUIDED_TOUR, SCREENSHOTS_MD):
        text = path.read_text()
        # Honest regeneration note is fine; claiming the on-disk PNG shows the banner is not.
        assert "with redirect banner" not in text
        assert "Sticky “Redirected: …” banner over Team Launcher" not in text
        assert "banner on regeneration" in text or "injects" in text.lower()


def test_spa_app_mobile_dock_omits_settings_tab():
    """SPA mobile dock stays five tabs; Settings is desktop/gear (matches mobile PNGs)."""
    app = (REPO / "webui" / "frontend" / "src" / "App.tsx").read_text()
    # Five MobileTab labels in the bottom nav; no Settings href tab.
    assert 'label="Sessions"' in app
    assert 'MobileTab href="/settings/"' not in app
    assert 'label="Chat"' in app


def test_feature_status_mobile_dock_omits_settings():
    """FEATURE_STATUS must not claim Settings is on the SPA mobile dock."""
    text = (REPO / "FEATURE_STATUS.md").read_text()
    # Stale claim paired Settings into the five-tab dock list.
    assert "mobile dock Home·Chat + Django hrefs (Blueprints·Teams·Sessions·Settings)" not in text
    assert "mobile five-tab dock" in text or "Settings is desktop top-nav" in text


def test_auth_summary_csp_has_no_style_residual():
    """AUTH.md overview must match prod CSP (no style-src unsafe-inline)."""
    text = (REPO / "docs" / "AUTH.md").read_text()
    assert "style residual" not in text
    assert "style-src self; no unsafe-inline" in text or (
        "script-src/style-src self" in text and "no unsafe-inline" in text
    )


def test_every_non_archive_png_listed_in_registry():
    """Every PNG under docs/screenshots/ (except archive/) must appear in SCREENSHOTS.md."""
    registry = SCREENSHOTS_MD.read_text()
    missing = []
    for path in _non_archive_screenshot_pngs():
        rel = _registry_rel(path)
        # Accept `skills/foo.png`, `webui/foo.png`, `mobile/foo.png`, or bare basename.
        if rel not in registry and path.name not in registry:
            missing.append(rel)
    assert not missing, f"PNGs missing from SCREENSHOTS.md registry: {missing}"


def test_skills_glob_not_a_substitute_for_per_file_rows():
    """Do not lump skills stills as skills/* — each file needs its own Used-in row."""
    registry = SCREENSHOTS_MD.read_text()
    assert "`docs/screenshots/skills/*`" not in registry
    assert "`skills/*`" not in registry
    for path in sorted((SCREENSHOTS_DIR / "skills").glob("*.png")):
        assert f"`skills/{path.name}`" in registry, f"missing skills row for {path.name}"


def test_webui_pngs_have_per_file_registry_rows():
    registry = SCREENSHOTS_MD.read_text()
    for path in sorted((SCREENSHOTS_DIR / "webui").glob("*.png")):
        assert f"`webui/{path.name}`" in registry, f"missing webui row for {path.name}"


def test_non_archive_pngs_embedded_or_marked_registry_only():
    """Orphans must be honest: embedded in docs, or Used-in none/registry-only."""
    registry = SCREENSHOTS_MD.read_text()
    embeds = _docs_png_embed_targets()
    dishonest = []
    for path in _non_archive_screenshot_pngs():
        rel = _registry_rel(path)
        if rel in embeds:
            continue
        # Find the registry table row that mentions this file.
        row = None
        for line in registry.splitlines():
            if f"`{rel}`" in line or (
                "/" not in rel and f"`{path.name}`" in line and line.strip().startswith("|")
            ):
                row = line
                break
        if row is None:
            dishonest.append(f"{rel}: no registry row")
            continue
        used_ok = any(m in row.lower() for m in ("none", "registry-only", "unused"))
        # Light twins / historical orphans are allowed; claiming a live Used-in without embed is not.
        if not used_ok:
            dishonest.append(f"{rel}: not embedded and Used-in is not registry-only/none ({row})")
    assert not dishonest, "registry honesty gaps:\n" + "\n".join(dishonest)


def test_skills_and_webui_doc_embeds_resolve_on_disk():
    """Captions in skills/webui docs must point at real files (no broken paths)."""
    embed_re = re.compile(r"!\[[^\]]*\]\(([^)]+\.png)\)")
    docs = [
        REPO / "docs" / "SKILLS_AND_CONSENSUS_WALKTHROUGH.md",
        REPO / "docs" / "examples" / "webui-config-panels.md",
        REPO / "docs" / "examples" / "inference-profile-routing.md",
        REPO / "docs" / "examples" / "tool-capabilities.md",
    ]
    missing = []
    for path in docs:
        text = path.read_text()
        for m in embed_re.finditer(text):
            rel = m.group(1)
            if rel.startswith("http"):
                continue
            target = (path.parent / rel).resolve()
            if not target.is_file():
                missing.append(f"{path.name}: {rel}")
    assert not missing, f"broken screenshot embeds: {missing}"


def test_guided_tour_embeds_mobile_spa_chat_when_captured():
    """High-value mobile spa-chat orphan must be embedded once the PNG exists."""
    if not (SCREENSHOTS_DIR / "mobile" / "spa-chat.png").is_file():
        pytest.skip("mobile/spa-chat.png not captured yet")
    text = GUIDED_TOUR.read_text()
    assert "mobile/spa-chat.png" in text, (
        "GUIDED_TOUR.md must embed screenshots/mobile/spa-chat.png when captured"
    )


def test_spa_chat_checked_in_caption_does_not_hardclaim_connected_badge():
    """Checked-in spa-chat PNGs show Connecting…; docs must not claim Connected as on-disk fact."""
    for path in (GUIDED_TOUR, SCREENSHOTS_MD):
        text = path.read_text()
        # Ban the old hard claim that checked-in frames are Connected.
        assert "both show the **Connected**" not in text
        assert "**Connected** composer + blueprint selector" not in text
        assert "**Connected** shell after journey login" not in text
        # Honest language for the checked-in frame.
        assert "Connecting…" in text or "Connecting" in text
