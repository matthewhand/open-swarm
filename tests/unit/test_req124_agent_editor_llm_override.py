"""REQ-124: Agent editor — role explanations + show default LLM on override (Fixes #511)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_EDITOR_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentEditor.tsx"
AGENT_EDITS_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "agentEdits.ts"


def test_agent_editor_role_explanation_and_remotes():
    tsx = AGENT_EDITOR_TSX.read_text(encoding="utf-8")
    # Role explanation blurb
    assert "ROLE_BRIEFS" in tsx
    assert 'data-testid="role-explanation"' in tsx

    # Remote agents: override disabled / greyed with reason
    assert "Remotes keep their own models" in tsx


def test_agent_editor_kind_appropriate_override_and_default_label():
    tsx = AGENT_EDITOR_TSX.read_text(encoding="utf-8")
    # Default visibility
    assert 'data-testid="default-llm-label"' in tsx
    assert "Default would be:" in tsx

    # CLI controls
    assert 'aria-label="CLI override"' in tsx
    assert "availableClis" in tsx
    assert "availableCliModels" in tsx

    # API controls
    assert 'aria-label="API profile override"' in tsx
    assert "availableApiModels" in tsx

    # Filter out agent names from model lists
    assert "catalogAgentIds" in tsx


def test_agent_edits_persists_cli_and_profile_overrides():
    ts = AGENT_EDITS_TS.read_text(encoding="utf-8")
    assert "cliOverride?: string" in ts
    assert "profileOverride?: string" in ts
    assert "patch.cliOverride !== undefined" in ts
    assert "patch.profileOverride !== undefined" in ts
