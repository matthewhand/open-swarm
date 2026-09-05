"""REQ-70 / #407: chrome is side-channel metadata; the UI reconstructs it."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from swarm.core.chat_compact import (
    build_model_context,
    compact_backlog,
    context_for_conversation,
    summarize_items,
)
from swarm.core.transcript_roles import (
    context_blob,
    reconstruct_display,
    split_store,
    turns_for_model,
)
from swarm.blueprints.common import cli_fusion_support as support


STATUS_CLI = "CLI: antigravity → grok"
STATUS_MESSAGED = "Messaged 3 Bots"
STATUS_FROM = "Message from Codey"
STATUS_FALLBACK = "Rate limited — retrying with grok"
INFO_CONNECTING = "Connecting…"


def _mixed_thread():
    return [
        {"role": "status", "content": STATUS_CLI, "ts": "2026-09-05T12:00:00+00:00"},
        {"role": "info", "content": INFO_CONNECTING, "ts": "2026-09-05T12:00:01+00:00"},
        {"role": "status", "content": STATUS_MESSAGED},
        {"role": "status", "content": STATUS_FROM},
        {"role": "info", "content": STATUS_FALLBACK},
        {"role": "user", "content": "hello there"},
        {"role": "assistant", "content": "hi back", "name": "jeeves"},
        {"role": "tool", "content": "ok", "name": "lookup", "tool_call_id": "c1"},
    ]


def _assert_no_chrome(payload: list[dict]):
    blob = context_blob(payload)
    for chrome in (STATUS_CLI, STATUS_MESSAGED, STATUS_FROM, STATUS_FALLBACK, INFO_CONNECTING):
        assert chrome not in blob
    roles = [m.get("role") for m in payload]
    assert "status" not in roles
    assert "info" not in roles


def test_append_seq_keeps_session_notice_before_assistant():
    from swarm.core.transcript_roles import append_event, append_turn

    turns: list[dict] = []
    events: list[dict] = []
    append_turn(turns, events, {"role": "user", "content": "hello"})
    append_event(turns, events, {"role": "status", "content": "Started a new grok session."})
    append_turn(turns, events, {"role": "assistant", "content": "hi"})
    assert [row["role"] for row in reconstruct_display(turns, events)] == [
        "user",
        "status",
        "assistant",
    ]


def test_split_store_keeps_chrome_out_of_turns():
    turns, events = split_store(_mixed_thread(), [])
    assert [(m["role"], m["content"]) for m in turns] == [
        ("user", "hello there"),
        ("assistant", "hi back"),
        ("tool", "ok"),
    ]
    assert {e["content"] for e in events} >= {
        STATUS_CLI,
        INFO_CONNECTING,
        STATUS_MESSAGED,
        STATUS_FROM,
        STATUS_FALLBACK,
    }
    for event in events:
        assert event["ts"]


def test_reconstruct_display_rebuilds_chrome_from_events():
    turns, events = split_store(_mixed_thread(), [])
    display = reconstruct_display(turns, events)
    texts = [row["content"] for row in display]
    assert texts[0] == STATUS_CLI
    assert "hello there" in texts
    assert "hi back" in texts
    assert STATUS_MESSAGED in texts
    assert all(row.get("ts") for row in display if row["role"] in {"status", "info"})


def test_turns_for_model_is_safety_belt_on_mixed_rows():
    payload = turns_for_model(_mixed_thread())
    assert [(m["role"], m["content"]) for m in payload] == [
        ("user", "hello there"),
        ("assistant", "hi back"),
        ("tool", "ok"),
    ]
    assert payload[1]["name"] == "jeeves"
    assert payload[2]["tool_call_id"] == "c1"
    _assert_no_chrome(payload)


def test_build_model_context_uses_turns_only():
    turns, _events = split_store(_mixed_thread(), [])
    payload = build_model_context(turns, [])
    assert [(m["role"], m["content"]) for m in payload] == [
        ("user", "hello there"),
        ("assistant", "hi back"),
        ("tool", "ok"),
    ]
    assert payload[1].get("name") == "jeeves"
    _assert_no_chrome(payload)
    _assert_no_chrome(build_model_context(_mixed_thread(), []))


def test_context_for_conversation_no_cid_uses_turns():
    payload = context_for_conversation("", _mixed_thread())
    _assert_no_chrome(payload)
    assert any(m["role"] == "user" and m["content"] == "hello there" for m in payload)
    assert any(m["role"] == "assistant" and m["content"] == "hi back" for m in payload)


def test_summarize_items_skips_chrome():
    body = summarize_items(
        [
            {"kind": "message", "role": "status", "content": STATUS_CLI},
            {"kind": "message", "role": "info", "content": INFO_CONNECTING},
            {"kind": "message", "role": "user", "content": "alpha question"},
            {"kind": "message", "role": "assistant", "content": "alpha answer"},
        ]
    )
    assert "alpha question" in body
    assert "alpha answer" in body
    assert STATUS_CLI not in body
    assert INFO_CONNECTING not in body
    assert "status" not in body
    assert "Summary of 2 items" in body


@pytest.mark.django_db
def test_compact_backlog_summarises_real_messages_only():
    from django.contrib.auth import get_user_model
    from swarm.core import chat_store

    user = get_user_model().objects.create_user(username="req70-compact", password="pw")
    cid = "conv-req70-compact"
    messages = [
        {"role": "status", "content": STATUS_CLI, "ts": "2026-09-05T01:00:00Z"},
        {"role": "user", "content": "remember this"},
        {"role": "assistant", "content": "ok"},
        {"role": "info", "content": STATUS_FALLBACK},
    ]
    chat_store.save(chat_store.user_key_for(user), "jeeves", messages, conversation_id=cid)
    loaded = chat_store.load(chat_store.user_key_for(user), "jeeves")
    assert [m["role"] for m in loaded["messages"]] == ["user", "assistant"]
    assert {e["content"] for e in loaded["ui_events"]} >= {STATUS_CLI, STATUS_FALLBACK}
    row, raw = compact_backlog(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=messages,
    )
    assert all(item.get("role") != "status" for item in raw)
    assert STATUS_CLI not in row.body
    assert STATUS_FALLBACK not in row.body
    assert "remember this" in row.body
    context = build_model_context(raw, [row])
    blob = context_blob(context)
    assert STATUS_CLI not in blob
    assert STATUS_FALLBACK not in blob
    assert any(m["role"] == "system" and "[Conversation summary]" in m["content"] for m in context)


@pytest.mark.django_db
def test_thread_post_stores_status_as_ui_event():
    import json

    from django.contrib.auth import get_user_model
    from django.test import Client

    get_user_model().objects.create_user(username="req70-ts", password="pw")
    client = Client()
    client.login(username="req70-ts", password="pw")
    resp = client.post(
        "/chat/thread/?agent=jeeves",
        data=json.dumps(
            {
                "message": {
                    "role": "info",
                    "content": STATUS_FALLBACK,
                }
            }
        ),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["turns"] == []
    assert body["ui_events"][-1]["content"] == STATUS_FALLBACK
    assert body["ui_events"][-1]["ts"]
    assert body["messages"][-1]["role"] in {"info", "status"}
    assert body["messages"][-1]["ts"]

    again = client.get("/chat/thread/?agent=jeeves")
    assert again.status_code == 200
    restored = again.json()
    assert restored["ui_events"][-1]["content"] == STATUS_FALLBACK
    assert restored["ui_events"][-1]["ts"] == body["ui_events"][-1]["ts"]
    assert all(row["role"] not in {"status", "info"} for row in restored["turns"])


def test_render_prompt_excludes_status_and_keeps_turns():
    prompt = support.render_prompt(
        [
            {"role": "status", "content": STATUS_CLI},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "ok", "name": "echo"},
            {"role": "user", "content": "again"},
        ]
    )
    assert STATUS_CLI not in prompt
    assert "hello" in prompt
    assert "again" in prompt
    assert "ok" in prompt


@pytest.mark.asyncio
async def test_compacted_context_exception_still_uses_turns_only():
    from swarm.consumers import _compacted_context

    thread = _mixed_thread()
    with patch(
        "swarm.core.chat_compact.context_for_conversation",
        side_effect=RuntimeError("db down"),
    ):
        payload = await _compacted_context("conv-x", thread)
    _assert_no_chrome(payload)
    assert any(m["role"] == "user" and m["content"] == "hello there" for m in payload)


@pytest.mark.asyncio
async def test_blueprint_run_payload_has_zero_status_strings(monkeypatch):
    from swarm.consumers import DjangoChatConsumer

    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    consumer = DjangoChatConsumer()
    consumer.conversation_id = "conv-req70"
    consumer.messages = [
        {"role": "user", "content": "hello there"},
        {"role": "assistant", "content": "hi back", "name": "jeeves"},
    ]
    consumer.ui_events = [
        {"kind": "status", "role": "status", "content": STATUS_CLI, "ts": "2026-09-05T12:00:00Z"},
    ]
    consumer.user = type("U", (), {"is_authenticated": False, "pk": None})()
    seen = {}

    async def fake_run(messages, **kwargs):
        seen["messages"] = messages
        yield {"messages": [{"role": "assistant", "content": "ok"}]}

    instance = MagicMock()
    instance.run = fake_run
    instance.metadata = {}
    instance.agents = None

    async def fake_context(conversation_id, messages, **kwargs):
        return build_model_context(messages, [])

    with patch("swarm.consumers._compacted_context", side_effect=fake_context):
        with patch("swarm.views.utils.get_blueprint_instance", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance
            with patch.object(consumer, "send", new_callable=AsyncMock):
                await consumer.respond_with_blueprint("jeeves", "message-response-req70")

    payload = seen["messages"]
    _assert_no_chrome(payload)
    assert any(m["content"] == "hello there" for m in payload)
    assert any(m["content"] == "hi back" for m in payload)


def test_schema1_mixed_file_migrates_on_load(tmp_path):
    from swarm.core import chat_store

    path = tmp_path / "active" / "u1" / "jeeves.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        """{
          "schema": 1,
          "agent_id": "jeeves",
          "user_key": "u1",
          "messages": [
            {"role": "user", "content": "hi"},
            {"role": "status", "content": "CLI: antigravity → grok"},
            {"role": "assistant", "content": "hello"}
          ]
        }
        """,
        encoding="utf-8",
    )
    loaded = chat_store.load("u1", "jeeves", base_dir=tmp_path)
    assert [m["role"] for m in loaded["messages"]] == ["user", "assistant"]
    assert loaded["ui_events"][0]["content"] == "CLI: antigravity → grok"
    display = chat_store.display_messages(loaded)
    assert [m["role"] for m in display] == ["user", "status", "assistant"]
