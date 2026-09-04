"""REQ-173: Remove edit pencils from left rail / sidepane (Fixes #627, Fixes #606)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_SIDEBAR_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"


def test_rail_rows_have_no_edit_pencils():
    content = AGENT_SIDEBAR_TSX.read_text(encoding="utf-8")

    # Hover pencil buttons on agent rows must be removed
    assert 'className="os-agent-edit"' not in content, "Hover pencil buttons must be removed from rail rows"
    assert "openBlueprintEditor" not in content, "Undefined openBlueprintEditor call site must be removed (Fixes #606)"
    assert "showsBlueprintEdit" not in content, "showsBlueprintEdit should not be needed in sidebar rows"

    # Context menu edit option must remain accessible
    assert "Edit agent" in content, "Edit agent context menu must remain available"
    assert 'role="menuitem"' in content
