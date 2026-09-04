"""REQ-28 chrome contracts: CoS rail is not support/gate/skeptic; team badge exists."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPA_CSS = REPO / "webui" / "frontend" / "src" / "index.css"
DJANGO_CSS = REPO / "src" / "swarm" / "static" / "css" / "rest_mode_style.css"
SIDEBAR_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"


def test_cos_badge_color_is_not_support_gate_or_skeptic():
    """REQ-28 distinct CoS colour survives REQ-67 (badge only, not row/dot)."""
    for css in (SPA_CSS.read_text(encoding="utf-8"), DJANGO_CSS.read_text(encoding="utf-8")):
        assert '.os-agent-role-badge[data-role="chief_of_staff"]' in css
        assert "#4f8ec9" in css  # CoS ice-steel
        assert "#3d8f8a" in css  # support teal
        assert css.index("#4f8ec9") != css.index("#3d8f8a")
        assert 'data-kind="team"' in css


def test_django_sidebar_fetches_rosters_and_badges_cos():
    js = SIDEBAR_JS.read_text(encoding="utf-8")
    assert "/v1/team-rosters/" in js
    assert "chief_of_staff" in js
    assert "Team" in js
    assert "/v1/teams/" not in js
