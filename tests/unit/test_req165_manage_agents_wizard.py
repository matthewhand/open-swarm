"""REQ-165: Manage existing CLI + API agents from Add-agent flow (#586).
REQ-167: CLI Folder workspace field — UI only (#590).
REQ-164 addendum: New agent bumped to top of unpinned rail (#585).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WIZARD_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AddAgentWizard.tsx"
SIDEBAR_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"
AGENT_EDITS_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "agentEdits.ts"


def test_add_agent_wizard_manage_surface():
    content = WIZARD_TSX.read_text(encoding="utf-8")
    # REQ-165: manage surface
    assert "manage-agent-surface" in content
    assert "empty-manage-state" in content
    assert "manage-agent-list" in content
    assert "No CLI agents yet" in content
    assert "No API agents yet" in content
    assert "add-new-agent-btn" in content
    assert "updateCustomBlueprint" in content


def test_cli_folder_field_and_validation():
    content = WIZARD_TSX.read_text(encoding="utf-8")
    # REQ-167: Folder field and help text
    assert 'data-testid="input-cli-folder"' in content
    assert "Working directory for this CLI agent" in content
    assert "isValidFolderPath" in content
    assert "folder-error" in content


def test_agent_edits_supports_folder_and_command():
    content = AGENT_EDITS_TS.read_text(encoding="utf-8")
    assert "folder?: string" in content
    assert "command?: string" in content
    assert "patch.folder !== undefined" in content
    assert "patch.command !== undefined" in content


def test_sidebar_unpinned_bump_and_select_agent():
    content = SIDEBAR_TSX.read_text(encoding="utf-8")
    # REQ-164 addendum: newly created agent placed at top of unpinned rail
    assert "bumpRailIdToTop(base, created.id)" in content
    assert "onSelectAgent={handleAgentSelected}" in content
