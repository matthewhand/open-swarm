"""Lock REQ-191 / #648 tip + Mode A/B contract (ADR-010).

Tip + ADR this PR. Mode B as-tool/handoff wiring is specified in the ADR
and deferred — do not claim it is implemented here.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs" / "adr" / "010-role-agent-invocation-modes.md"
ADR_INDEX = REPO / "docs" / "adr" / "README.md"
REQ = REPO / "docs" / "requirements" / "REQ-191.md"
REQ_INDEX = REPO / "docs" / "requirements" / "README.md"
CHAT = REPO / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"
TIP = REPO / "webui" / "frontend" / "src" / "components" / "RoleAgentTip.tsx"
LIB = REPO / "webui" / "frontend" / "src" / "lib" / "roleAgentTip.ts"
ROLES = REPO / "webui" / "frontend" / "src" / "lib" / "agentRoles.ts"
TIPS = REPO / "webui" / "frontend" / "src" / "lib" / "keybindingTips.ts"


def test_adr010_contract_and_deferred_mode_b():
    text = ADR.read_text(encoding="utf-8")
    assert "REQ-191" in text
    assert "#648" in text
    assert "Mode A" in text
    assert "Mode B" in text
    assert "full conversation" in text.lower() or "full thread" in text.lower()
    assert "caller" in text.lower()
    assert "latest message" in text.lower()
    assert "as_tool" in text or "as-tool" in text
    assert "handoff" in text
    assert "deferred" in text.lower()
    assert "role_agent_tip_dismissed" in text
    assert "#540" in text or "preferences" in text
    assert "#571" in text or "#577" in text
    assert "#356" in text
    assert "#564" in text
    assert "REQ-191B" in text or "child" in text.lower()


def test_adr010_is_indexed_and_req_pointer_exists():
    index = ADR_INDEX.read_text(encoding="utf-8")
    assert "010-role-agent-invocation-modes.md" in index
    assert "REQ-191" in index
    req = REQ.read_text(encoding="utf-8")
    assert "https://github.com/matthewhand/open-swarm/issues/648" in req
    assert "010-role-agent-invocation-modes.md" in req
    req_index = REQ_INDEX.read_text(encoding="utf-8")
    assert "REQ-191.md" in req_index
    assert "#648" in req_index


def test_chat_pane_tip_not_overlay_and_not_first_load_tips():
    chat = CHAT.read_text(encoding="utf-8")
    tip = TIP.read_text(encoding="utf-8")
    lib = LIB.read_text(encoding="utf-8")
    roles = ROLES.read_text(encoding="utf-8")
    keybinding = TIPS.read_text(encoding="utf-8")

    assert "RoleAgentTip" in chat
    assert "shouldShowRoleAgentTip" in chat
    assert "role-agent-tip" in tip
    assert "Dismiss role tip" in tip
    assert "role=\"dialog\"" not in tip
    assert "first-load-tips" not in chat
    assert "KeybindingTips" not in chat
    assert "Dismissible overlay chrome is gone" in keybinding
    assert "ROLE_AGENT_TIP_STORAGE_KEY" in lib
    assert "role_agent_tip_dismissed" in lib
    assert "agentHasRole" in roles
    assert "agentRole(agent) !== 'default'" in roles
