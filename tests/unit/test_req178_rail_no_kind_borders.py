"""REQ-178: No special border chrome on team/remote rail rows (Fixes #633)."""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_CSS = REPO_ROOT / "webui" / "frontend" / "src" / "index.css"


def test_no_persistent_kind_borders_on_team_and_remote_rows():
    css = INDEX_CSS.read_text(encoding="utf-8")

    # Team rows must not have a persistent kind-coloured inset border
    assert not re.search(r"\.os-agent-row--team\s*\{[^}]*?box-shadow:\s*inset 2px 0 0 #6b7c8a", css)

    # Remote rows must not have a persistent kind-coloured inset border
    assert not re.search(r"\.os-agent-row--remote\s*\{[^}]*?box-shadow:\s*inset 2px 0 0 #5a7a6a", css)

    # Inset 2px border should not exist anywhere for agent rows
    assert "inset 2px 0 0 #6b7c8a" not in css
    assert "inset 2px 0 0 #5a7a6a" not in css
