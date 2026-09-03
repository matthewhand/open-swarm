"""REQ-6: original Bert-like default agent avatar is wired as the fallback."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AVATAR = REPO / "src" / "swarm" / "static" / "img" / "default-agent-avatar.svg"
SPA_AVATAR = REPO / "webui" / "frontend" / "src" / "assets" / "default-agent-avatar.svg"
SIDEBAR_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"
SPA_SIDEBAR = REPO / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"
SPA_AVATAR_TSX = REPO / "webui" / "frontend" / "src" / "components" / "AgentAvatar.tsx"
CHAT = REPO / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"
CARD = REPO / "src" / "swarm" / "templates" / "blueprint_card.html"


def test_original_svg_exists_and_is_not_a_raster_still():
    svg = AVATAR.read_text(encoding="utf-8")
    assert AVATAR.is_file()
    assert svg.lstrip().startswith("<svg")
    assert "png" not in svg.lower()
    # Cyan pear + white eyes + dark pupils — the small-size read.
    assert "#3deef5" in svg.lower()
    assert "#ffffff" in svg.lower()
    assert "#141414" in svg
    assert svg.count("<circle") >= 4
    assert "Not a copy of any film/TV still" in svg
    # SPA ships the same original drawing (Vite import), not a Trap Door still.
    assert SPA_AVATAR.read_text(encoding="utf-8") == svg


def test_django_sidebar_and_library_card_use_default_svg():
    js = SIDEBAR_JS.read_text(encoding="utf-8")
    assert "/static/img/default-agent-avatar.svg" in js
    assert "os-agent-dot" not in js
    card = CARD.read_text(encoding="utf-8")
    assert "img/default-agent-avatar.svg" in card
    assert "fa-robot" not in card


def test_spa_wires_agent_avatar_as_default():
    avatar = SPA_AVATAR_TSX.read_text(encoding="utf-8")
    sidebar = SPA_SIDEBAR.read_text(encoding="utf-8")
    chat = CHAT.read_text(encoding="utf-8")
    assert "default-agent-avatar.svg" in avatar
    assert "AgentAvatar" in sidebar
    assert "os-agent-dot" not in sidebar
    assert "agentMarkIndex" not in sidebar
    assert "AgentAvatar" in chat
    # Custom avatar_path must reach all three chat faces (header / empty / bubbles).
    assert chat.count("src={agentAvatarSrc}") == 3
    assert "selectedAgent?.avatar_path" in chat
