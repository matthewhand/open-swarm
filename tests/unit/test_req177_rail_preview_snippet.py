from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAT_TIME_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "chatTime.ts"
AGENT_CHAT_SESSIONS_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "agentChatSessions.ts"
SIDEBAR_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"
CHAT_PAGE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"


def test_chat_time_exports_preview_snippet_helpers():
    """chatTime.ts must export selectLatestMessage and truncateSnippet for REQ-177."""
    content = CHAT_TIME_TS.read_text(encoding="utf-8")
    assert "export function selectLatestMessage(" in content
    assert "export function truncateSnippet(" in content
    assert "export const PREVIEW_SNIPPET_MAX_CHARS = 100" in content
    assert "role === 'assistant'" in content
    assert "role === 'user'" in content


def test_agent_chat_sessions_dispatches_change_event():
    """agentChatSessions.ts must dispatch AGENT_CHAT_SESSIONS_EVENT upon save."""
    content = AGENT_CHAT_SESSIONS_TS.read_text(encoding="utf-8")
    assert "export const AGENT_CHAT_SESSIONS_EVENT = 'swarm:agent-chat-sessions'" in content
    assert "export function emitAgentChatSessionsChanged(" in content
    assert "emitAgentChatSessionsChanged(agentId)" in content


def test_sidebar_listens_to_agent_chat_sessions_event():
    """AgentSidebar.tsx must listen to AGENT_CHAT_SESSIONS_EVENT for live updates."""
    content = SIDEBAR_TSX.read_text(encoding="utf-8")
    assert "AGENT_CHAT_SESSIONS_EVENT" in content
    assert "window.addEventListener(AGENT_CHAT_SESSIONS_EVENT, onChange)" in content


def test_chat_page_syncs_messages_for_rail_preview():
    """ChatPage.tsx must sync active thread messages to localStorage for live rail updates."""
    content = CHAT_PAGE_TSX.read_text(encoding="utf-8")
    assert "putAgentChatSession(activeChatAgentId" in content
    assert "persistableMessages" in content
