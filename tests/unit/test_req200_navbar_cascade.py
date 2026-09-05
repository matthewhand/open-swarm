"""REQ-200: one cascading navbar picker (Fixes #676)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAT_PAGE = REPO_ROOT / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"
PICKER = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "NavbarRoutingPicker.tsx"
PATH_LIB = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "routingPath.ts"
SETTINGS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "agentSettings.ts"
STATUS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "chatStatus.ts"


def test_navbar_uses_one_cascading_picker_not_sibling_selects():
    chat = CHAT_PAGE.read_text(encoding="utf-8")
    picker = PICKER.read_text(encoding="utf-8")
    path_lib = PATH_LIB.read_text(encoding="utf-8")
    settings = SETTINGS.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")

    assert "NavbarRoutingPicker" in chat
    assert "applyCliRoutingChange" in chat
    assert 'data-testid="cli-select"' not in chat
    assert 'data-testid="cli-model-select"' not in chat
    assert 'data-testid="api-select"' not in chat
    assert 'data-testid="api-model-select"' not in chat
    assert "availableApiAgents" not in chat
    assert 'data-testid="api-select"' not in picker
    assert "availableApiAgents" not in picker

    assert "navbar-routing-picker" in picker
    assert "routing-pill-agent" in picker
    assert "routing-pill-model" in picker
    assert "routing-pill-effort" in picker
    assert "ArrowDown" in picker
    assert "Escape" in picker
    assert "rtl" in picker
    assert "routing-sheet" in picker

    assert "HIDDEN_ROUTING_LABELS" in path_lib
    assert "you" in path_lib
    assert "gemini-3.8-flash" not in path_lib  # do not invent models
    assert "'effort'" in settings or '"effort"' in settings
    assert "effort" in status


def test_no_live_host_or_secrets_in_req200_surface():
    for path in (CHAT_PAGE, PICKER, PATH_LIB):
        text = path.read_text(encoding="utf-8")
        assert ":8001" not in text
        # OpenAI-style secret prefix, not the `sk-` substring inside `task-`.
        assert re.search(r"(?<![A-Za-z])sk-[A-Za-z0-9]", text) is None
        assert "OPENAI_API_KEY" not in text
        assert "localhost:8001" not in text
