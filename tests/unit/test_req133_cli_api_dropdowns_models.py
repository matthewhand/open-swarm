"""REQ-133: CLI chat dropdowns with model selectors (Fixes #523).

API You/Default chrome (`api-select`) was removed in #751 / REQ-186.
This contract keeps the CLI + model picker that still exist on ChatPage.
"""

from pathlib import Path
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
import json

from swarm.core import chat_store

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAT_PAGE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"
CLI_CONTEXT_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "cliAgentContext.ts"
CHAT_STATUS_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "chatStatus.ts"


def test_chat_page_renders_cli_dropdowns_with_models():
    tsx = CHAT_PAGE_TSX.read_text(encoding="utf-8")
    assert "isCliAgent" in tsx
    assert "isApiAgent" in tsx
    assert "showRemotesControl" in tsx

    # CLI + model picker still on ChatPage
    assert 'data-testid="cli-select"' in tsx
    assert 'aria-label="CLI"' in tsx
    assert 'data-testid="cli-model-select"' in tsx

    # #751 removed You/Default API chrome — do not require it here (REQ-186 forbids it)
    assert 'data-testid="api-select"' not in tsx
    assert 'aria-label="API"' not in tsx
    assert "recordDropdownChange('api'" not in tsx

    # Status tracking on remaining dropdowns
    assert "recordDropdownChange('cli'" in tsx
    assert "recordDropdownChange('model'" in tsx


def test_chat_status_and_cli_context_contracts():
    status_ts = CHAT_STATUS_TS.read_text(encoding="utf-8")
    assert "'api'" in status_ts
    assert "'cli'" in status_ts
    assert "'model'" in status_ts
    assert "formatDropdownStatus" in status_ts

    cli_ts = CLI_CONTEXT_TS.read_text(encoding="utf-8")
    assert "discoverChatClis" in cli_ts
    assert "preferredChatCli" in cli_ts
    assert "isCliAgentContext" in cli_ts


@pytest.mark.django_db
def test_chat_thread_post_appends_status_line():
    user = get_user_model().objects.create_user(username="req133-tester", password="pw")
    client = Client()
    client.login(username="req133-tester", password="pw")

    resp = client.post(
        "/chat/thread/?agent=codey",
        data=json.dumps({"message": {"role": "status", "content": "CLI: antigravity → grok"}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert any(m["role"] == "status" and m["content"] == "CLI: antigravity → grok" for m in data["messages"])
    assert any(e["content"] == "CLI: antigravity → grok" for e in data["ui_events"])
    assert all(m["role"] != "status" for m in data["turns"])

    loaded = chat_store.load(chat_store.user_key_for(user), "codey")
    assert loaded is not None
    assert loaded["ui_events"][-1]["content"] == "CLI: antigravity → grok"
    assert all(m.get("role") != "status" for m in loaded["messages"])
