"""REQ-28 chrome contracts: CoS rail is not support/gate/skeptic; team badge exists."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPA_CSS = REPO / "webui" / "frontend" / "src" / "index.css"
DJANGO_CSS = REPO / "src" / "swarm" / "static" / "css" / "rest_mode_style.css"
SIDEBAR_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"


def test_cos_color_is_not_support_gate_or_skeptic():
    for css in (SPA_CSS.read_text(encoding="utf-8"), DJANGO_CSS.read_text(encoding="utf-8")):
        assert 'data-role="chief_of_staff"] { background: #4f8ec9; }' in css
        assert "#3d8f8a" in css  # support teal
        assert "#c9a227" in css  # gate amber
        assert "#8a5a9b" in css  # skeptic violet
        assert css.index("#4f8ec9") != css.index("#3d8f8a")
        assert 'data-kind="team"' in css


def test_django_sidebar_fetches_rosters_and_badges_cos():
    js = SIDEBAR_JS.read_text(encoding="utf-8")
    assert "/v1/team-rosters/" in js
    assert "chief_of_staff" in js
    assert "Team" in js
    assert "/v1/teams/" not in js
