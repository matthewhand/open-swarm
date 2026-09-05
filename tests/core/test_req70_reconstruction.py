"""REQ-70 / #789: status/info live as reconstructed UI metadata, not mixed store."""

from __future__ import annotations

import json

import pytest

from swarm.core.chat_compact import build_model_context, compact_backlog
from swarm.core.transcript_roles import (
    append_event,
    append_turn,
    build_model_context_from_store,
    context_blob,
    messages_for_model,
    reconstruct_display,
    split_store,
    turns_for_model,
)

STATUS_CLI = "CLI: antigravity → grok"
STATUS_HOP = "Messaged 3 Bots"
STATUS_FROM = "Message from Codey"
INFO_FAIL = "Rate limited — retrying with grok"


def _assert_no_chrome(payload: list[dict]) -> None:
    blob = context_blob(payload)
    for chrome in (STATUS_CLI, STATUS_HOP, STATUS_FROM, INFO_FAIL):
        assert chrome not in blob
    roles = [item.get("role") for item in payload]
    assert "status" not in roles
    assert "info" not in roles


def test_split_store_moves_chrome_out_of_turns():
    turns, events = split_store(
        [
            {"role": "user", "content": "hello"},
            {"role": "status", "content": STATUS_CLI, "ts": "2026-09-05T12:00:00Z"},
            {"role": "assistant", "content": "hi"},
            {"role": "info", "content": INFO_FAIL},
            {"role": "status", "content": STATUS_HOP},
        ]
    )
    assert [row["role"] for row in turns] == ["user", "assistant"]
    assert [row["content"] for row in events] == [STATUS_CLI, INFO_FAIL, STATUS_HOP]
    assert all(event.get("ts") for event in events)
    assert events[2]["kind"] == "hop"


def test_reconstruct_keeps_user_status_assistant_order():
    turns: list[dict] = []
    events: list[dict] = []
    append_turn(turns, events, "user", "hello")
    append_event(turns, events, "status", STATUS_CLI, ts="2026-09-05T12:00:00Z")
    append_turn(turns, events, "assistant", "hi")
    display = reconstruct_display(turns, events)
    assert [row["role"] for row in display] == ["user", "status", "assistant"]
    assert display[1]["content"] == STATUS_CLI
    assert display[1]["ts"] == "2026-09-05T12:00:00Z"
    assert [row["role"] for row in turns] == ["user", "assistant"]


def test_model_context_from_store_is_turns_only_not_filter_on_mixed():
    turns, events = split_store(
        [
            {"role": "status", "content": STATUS_CLI},
            {"role": "user", "content": "hello there"},
            {"role": "assistant", "content": "hi back"},
            {"role": "status", "content": STATUS_FROM},
        ]
    )
    payload = build_model_context_from_store(turns, events)
    assert [(row["role"], row["content"]) for row in payload] == [
        ("user", "hello there"),
        ("assistant", "hi back"),
    ]
    _assert_no_chrome(payload)
    assert turns_for_model(turns) == messages_for_model(turns)


def test_schema1_mixed_file_migrates_on_load(tmp_path):
    from swarm.core import chat_store

    path = tmp_path / "active" / "u1" / "jeeves.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "agent_id": "jeeves",
                "user_key": "u1",
                "messages": [
                    {"role": "user", "content": "hi"},
                    {"role": "status", "content": STATUS_CLI, "ts": "2026-09-05T01:00:00Z"},
                    {"role": "assistant", "content": "hello"},
                ],
            }
        ),
        encoding="utf-8",
    )
    loaded = chat_store.load("u1", "jeeves", base_dir=tmp_path)
    assert [row["role"] for row in loaded["messages"]] == ["user", "assistant"]
    assert loaded["ui_events"][0]["content"] == STATUS_CLI
    assert loaded["ui_events"][0]["ts"] == "2026-09-05T01:00:00Z"
    display = reconstruct_display(loaded["messages"], loaded["ui_events"])
    assert [row["role"] for row in display] == ["user", "status", "assistant"]


def test_save_persists_chrome_in_ui_events(tmp_path):
    from swarm.core import chat_store

    chat_store.save(
        "u1",
        "jeeves",
        [
            {"role": "user", "content": "hi"},
            {"role": "status", "content": STATUS_CLI, "ts": "2026-09-05T12:00:00Z"},
            {"role": "assistant", "content": "hello"},
        ],
        base_dir=tmp_path,
    )
    raw = json.loads((tmp_path / "active" / "u1" / "jeeves.json").read_text(encoding="utf-8"))
    assert raw["schema"] == 2
    assert [row["role"] for row in raw["messages"]] == ["user", "assistant"]
    assert raw["ui_events"][0]["content"] == STATUS_CLI
    assert raw["ui_events"][0]["ts"] == "2026-09-05T12:00:00Z"


@pytest.mark.django_db
def test_compact_backlog_summarises_turns_only(stub_compact_llm):
    from django.contrib.auth import get_user_model
    from swarm.core import chat_store

    user = get_user_model().objects.create_user(username="req70-recon-compact", password="pw")
    cid = "conv-req70-recon-compact"
    mixed = [
        {"role": "status", "content": STATUS_CLI, "ts": "2026-09-05T01:00:00Z"},
        {"role": "user", "content": "remember this"},
        {"role": "assistant", "content": "ok"},
        {"role": "info", "content": INFO_FAIL},
    ]
    chat_store.save(chat_store.user_key_for(user), "jeeves", mixed, conversation_id=cid)
    row, raw = compact_backlog(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=mixed,
    )
    assert [item["role"] for item in raw] == ["user", "assistant"]
    assert STATUS_CLI not in row.body
    assert INFO_FAIL not in row.body
    assert row.body == "LLM digest of the compacted range."
    sent = stub_compact_llm[-1]["items"]
    assert any(item.get("content") == "remember this" for item in sent)
    context = build_model_context(raw, [row])
    _assert_no_chrome(context)


@pytest.mark.django_db
def test_thread_post_status_lands_in_ui_events():
    from django.contrib.auth import get_user_model
    from django.test import Client
    from swarm.core import chat_store

    user = get_user_model().objects.create_user(username="req70-recon-post", password="pw")
    client = Client()
    client.login(username="req70-recon-post", password="pw")
    resp = client.post(
        "/chat/thread/?agent=jeeves",
        data=json.dumps({"message": {"role": "status", "content": STATUS_CLI}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["messages"][-1]["role"] == "status"
    assert body["messages"][-1]["ts"]
    assert body["ui_events"][-1]["content"] == STATUS_CLI
    assert all(row["role"] != "status" for row in body["turns"])

    loaded = chat_store.load(chat_store.user_key_for(user), "jeeves")
    assert all(row["role"] != "status" for row in loaded["messages"])
    assert loaded["ui_events"][-1]["content"] == STATUS_CLI
    assert loaded["ui_events"][-1]["ts"]


def test_prior_history_stays_system_chrome_not_a_turn():
    turns, events = split_store(
        [
            {
                "role": "system",
                "kind": "prior_history",
                "content": "**User:** old",
            },
            {"role": "user", "content": "next"},
        ]
    )
    assert [row["role"] for row in turns] == ["user"]
    assert events[0]["kind"] == "prior_history"
    assert events[0]["role"] == "system"
    payload = build_model_context_from_store(turns, events)
    assert payload == [{"role": "user", "content": "next"}]
    display = reconstruct_display(turns, events)
    assert display[0]["kind"] == "prior_history"
    assert display[0]["role"] == "system"
