from pathlib import Path


def test_req179_no_visible_names_in_agent_message_bubble():
    repo_root = Path(__file__).resolve().parents[2]
    bubble_tsx = (
        repo_root
        / "webui"
        / "frontend"
        / "src"
        / "components"
        / "AgentChat"
        / "AgentMessageBubble.tsx"
    )
    assert bubble_tsx.exists()
    content = bubble_tsx.read_text(encoding="utf-8")

    # Verifies no visible message.agent rendered above chat bubbles
    assert "{!isUser && message.agent && (" not in content
    # Verifies no visible message.agent appended to review bubble header
    assert "{message.agent ? ` · ${message.agent}` : ''}" not in content
    # Verifies accessible aria-label is present
    assert "aria-label=" in content
    assert "speaker" in content


def test_req179_chat_message_bubble_preserves_no_names_and_edited():
    repo_root = Path(__file__).resolve().parents[2]
    bubble_tsx = (
        repo_root
        / "webui"
        / "frontend"
        / "src"
        / "components"
        / "ChatMessageBubble.tsx"
    )
    assert bubble_tsx.exists()
    content = bubble_tsx.read_text(encoding="utf-8")

    # Verifies no visible speaker name above chat bubbles
    assert "{role === 'user' ? 'You' : agentName}" not in content
    # Verifies accessibility aria-label is present
    assert "aria-label=" in content
    # Verifies edited indicator is preserved
    assert 'data-testid="edited-hint"' in content
