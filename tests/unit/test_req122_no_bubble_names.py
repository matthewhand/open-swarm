from pathlib import Path


def test_req122_no_visible_names_in_chat_bubble_header():
    repo_root = Path(__file__).resolve().parents[2]
    bubble_tsx = repo_root / "webui" / "frontend" / "src" / "components" / "ChatMessageBubble.tsx"
    assert bubble_tsx.exists()
    content = bubble_tsx.read_text(encoding="utf-8")

    # Verifies no visible "You" or agentName label rendered above chat bubbles
    assert "{role === 'user' ? 'You' : agentName}" not in content
    # Verifies accessibility aria-label is present
    assert "aria-label=" in content
    # Verifies edited indicator is preserved
    assert 'data-testid="edited-hint"' in content
