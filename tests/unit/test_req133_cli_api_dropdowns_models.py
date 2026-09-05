"""REQ-133: CLI dropdown status lines persist on the chat thread (Fixes #523).

SPA picker / CLI-discovery contracts live in Vitest (`npm test` in the
Python Tests `vitest` job — REQ-171C-7 / #616). This file no longer greps
ChatPage testids or `cliAgentContext.ts` as a coverage substitute.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
import json

from swarm.core import chat_store


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
    status = next(m for m in data["messages"] if m["role"] == "status")
    assert status["content"] == "CLI: antigravity → grok"
    assert status.get("ts")

    loaded = chat_store.load(chat_store.user_key_for(user), "codey")
    assert loaded is not None
    assert loaded["ui_events"][-1]["content"] == "CLI: antigravity → grok"
    assert loaded["ui_events"][-1].get("ts")
    assert all(row["role"] != "status" for row in loaded["messages"])
