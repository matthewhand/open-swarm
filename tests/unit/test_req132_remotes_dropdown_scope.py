"""REQ-132: Remotes dropdown only on remote agents (not every agent)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAT_PAGE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"
CHAT_PAGE_TEST_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "pages" / "__tests__" / "ChatPage.test.tsx"


def test_chat_page_guards_remotes_dropdown():
    tsx = CHAT_PAGE_TSX.read_text(encoding="utf-8")
    assert "isRemoteBackedTeam" in tsx
    assert "isRemoteAgent" in tsx
    assert "showRemotesControl" in tsx

    # Must be conditionally rendered, omitted entirely when false (no empty stub)
    assert "{showRemotesControl ? (" in tsx
    assert "<RemoteSelect" in tsx
    assert ") : null}" in tsx


def test_chat_page_test_covers_req132():
    test_tsx = CHAT_PAGE_TEST_TSX.read_text(encoding="utf-8")
    assert "hides the Remotes control on local API and CLI agents" in test_tsx
    assert "hides the Remotes control on local teams" in test_tsx
    assert "shows the Remotes control on remote-backed teams" in test_tsx
