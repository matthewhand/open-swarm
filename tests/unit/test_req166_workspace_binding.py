"""REQ-166 / #589 — Phase 0 workspace binding chrome (UI only).

Source-lock so Add-agent + manage/edit show Folder for CLI and coming-soon
repo/workspaces stubs. No session cwd, checkout, or worktree wiring in this
slice. No secrets. No live :8001.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO / "webui" / "frontend" / "src" / "lib" / "agentWorkspace.ts"
BINDING = REPO / "webui" / "frontend" / "src" / "components" / "AgentWorkspaceBinding.tsx"
WIZARD = REPO / "webui" / "frontend" / "src" / "components" / "AddAgentWizard.tsx"
EDITOR = REPO / "webui" / "frontend" / "src" / "components" / "AgentEditor.tsx"
CI = REPO / ".github" / "workflows" / "req166-workspace-binding.yml"


def test_workspace_copy_and_validation_chrome():
    text = WORKSPACE.read_text(encoding="utf-8")
    assert "REQ-166" in text
    assert "Where this agent works" in text
    assert "Working directory for this CLI agent" in text
    assert "Coming soon" in text
    assert "owner/repo" in text
    assert "git worktree" in text
    assert "isValidGithubRepo" in text
    assert "workspacesEnabled" in text
    assert "checkout" in text.lower()
    assert "WAVE" not in text
    assert "ghp_" not in text
    assert ":8001" not in text
    assert "neon" not in text.lower()


def test_binding_component_covers_kinds_and_stubs():
    text = BINDING.read_text(encoding="utf-8")
    assert "agent-workspace-binding" in text
    assert "input-cli-folder" in text
    assert "input-github-repo" in text
    assert "toggle-workspaces" in text
    assert "disabled" in text
    assert "COMING_SOON_LABEL" in text
    assert "workspace-kind-stub" in text
    assert "workspace-folder-empty" in text
    assert "No checkout or worktree" in text


def test_surfaces_mount_workspace_chrome():
    wizard = WIZARD.read_text(encoding="utf-8")
    editor = EDITOR.read_text(encoding="utf-8")
    assert "AgentWorkspaceBinding" in wizard
    assert "AgentWorkspaceBinding" in editor
    assert 'kind="cli"' in wizard
    assert 'kind="api"' in wizard
    assert 'kind="remote"' in wizard
    assert "githubRepo" in wizard
    assert "githubRepo" in editor


def test_own_diff_ci_exists():
    text = CI.read_text(encoding="utf-8")
    assert "req166" in text.lower() or "REQ-166" in text
    assert "vitest" in text
    assert "pytest" in text
    assert ":8001" not in text
