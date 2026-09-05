"""REQ-121: cull vs compress, start-from-here, over-full warning.

No live host. No secrets. Distinct from #444 summariser and #672 LLM compact.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from swarm.core import chat_store
from swarm.core.context_cull_policy import (
    AUTO_CULL_INFO,
    DEFAULT_CONTEXT_STRATEGY,
    DEFAULT_CULL_FRACTION_PCT,
    DEFAULT_CULL_TRIGGER_PCT,
    EVENT_START_FROM_HERE,
    STRATEGY_CULL,
    UNKNOWN_MAX_CULL_INFO,
    apply_context_start,
    auto_cull_before_send,
    choose_cull_start,
    load_context_meta,
    load_context_policy,
    normalize_context_strategy,
    normalize_cull_fraction_pct,
    normalize_cull_trigger_pct,
    prepare_context_before_send,
    preview_start_from_here,
    would_warn_after_start,
)
from swarm.core.user_preferences import public_payload
from swarm.models.preferences import UserPreference


def _turns(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"role": role, "content": content} for role, content in pairs]


def _seed_json(user, agent, messages, conversation_id):
    chat_store.save(
        chat_store.user_key_for(user),
        agent,
        messages,
        conversation_id=conversation_id,
    )


def test_normalize_strategy_and_cull_defaults():
    assert normalize_context_strategy(None) == DEFAULT_CONTEXT_STRATEGY
    assert normalize_context_strategy("CULL") == STRATEGY_CULL
    assert normalize_cull_trigger_pct(None) == DEFAULT_CULL_TRIGGER_PCT
    assert normalize_cull_trigger_pct(90) == 90
    assert normalize_cull_trigger_pct(0) == 1
    assert normalize_cull_trigger_pct(200) == 99
    assert normalize_cull_fraction_pct(None) == DEFAULT_CULL_FRACTION_PCT
    assert normalize_cull_fraction_pct(50) == 50


def test_public_payload_defaults_are_compress_80_cull_90_50():
    payload = public_payload(principal="user:alice", guest=False, empty=True)
    assert payload["context_strategy"] == "compress"
    assert payload["context_auto_compress_pct"] == 80
    assert payload["context_cull_trigger_pct"] == 90
    assert payload["context_cull_fraction_pct"] == 50
    keys = [item["key"] for item in payload["registry"]]
    assert "context_strategy" in keys
    assert "context_cull_trigger_pct" in keys
    assert "context_cull_fraction_pct" in keys
    blob = str(payload)
    assert "sk-" not in blob
    assert "api_key" not in blob


def test_choose_cull_start_keeps_recent_suffix():
    assert choose_cull_start(1) is None
    assert choose_cull_start(2, fraction_pct=50) == 1
    assert choose_cull_start(10, current_start=0, fraction_pct=50) == 5
    assert choose_cull_start(10, current_start=5, fraction_pct=50) == 7
    # Recent offsets 7,8,9 stay the same after a second cull.
    assert apply_context_start(["a", "b", "c", "d"], 2) == ["c", "d"]


def test_would_warn_requires_known_max():
    assert would_warn_after_start(90, None, 90) is False
    assert would_warn_after_start(89, 100, 90) is False
    assert would_warn_after_start(90, 100, 90) is True


@pytest.mark.django_db
def test_settings_patch_cull_knobs_are_read_by_helper():
    user = get_user_model().objects.create_user("cull-settings", password="pw")
    client = APIClient()
    client.force_login(user)
    resp = client.patch(
        "/v1/preferences/",
        {
            "context_strategy": "cull",
            "context_cull_trigger_pct": 85,
            "context_cull_fraction_pct": 40,
        },
        format="json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["context_strategy"] == "cull"
    assert body["context_cull_trigger_pct"] == 85
    assert body["context_cull_fraction_pct"] == 40
    assert "sk-" not in str(body)
    policy = load_context_policy(user)
    assert policy.strategy == "cull"
    assert policy.cull_trigger_pct == 85
    assert policy.cull_fraction_pct == 40


@pytest.mark.django_db
def test_auto_cull_drops_oldest_half_and_keeps_suffix():
    user = get_user_model().objects.create_user("cull-auto", password="pw")
    UserPreference.objects.create(
        user=user,
        principal="user:cull-auto",
        values={
            "context_strategy": "cull",
            "context_cull_trigger_pct": 50,
            "context_cull_fraction_pct": 50,
        },
    )
    cid = "conv-cull-auto"
    messages = _turns(
        ("user", "old-a " * 80),
        ("assistant", "old-b " * 80),
        ("user", "mid-c " * 80),
        ("assistant", "mid-d " * 80),
        ("user", "keep-e " * 80),
        ("assistant", "keep-f " * 80),
    )
    _seed_json(user, "jeeves", messages, cid)
    from swarm.core.context_compress_policy import estimate_context_tokens

    estimated = estimate_context_tokens(messages)
    result = auto_cull_before_send(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=messages,
        inference_entry={"context_length": max(20, estimated)},
        trigger_pct=50,
        fraction_pct=50,
    )
    assert result.acted is True
    assert result.reason == "culled"
    assert result.info == AUTO_CULL_INFO.format(fraction=50)
    assert result.start_offset == 3
    contents = [row.get("content") for row in result.context]
    assert any("keep-e" in str(item) for item in contents)
    assert any("keep-f" in str(item) for item in contents)
    assert not any("old-a" in str(item) for item in contents)
    assert not any("old-b" in str(item) for item in contents)
    meta = load_context_meta(cid)
    assert meta["start_offset"] == 3
    assert meta["last_event"]["kind"] == "cull"
    blob = str(result.context) + str(meta)
    assert "sk-" not in blob


@pytest.mark.django_db
def test_unknown_max_skips_auto_cull():
    user = get_user_model().objects.create_user("cull-unknown", password="pw")
    cid = "conv-cull-unknown"
    messages = _turns(
        ("user", "alpha " * 40),
        ("assistant", "beta " * 40),
        ("user", "gamma " * 40),
        ("assistant", "delta " * 40),
    )
    result = auto_cull_before_send(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=messages,
        model_id="mystery-model",
    )
    assert result.acted is False
    assert result.reason == "unknown_max"
    assert result.info == UNKNOWN_MAX_CULL_INFO
    assert result.max_context is None
    assert load_context_meta(cid)["start_offset"] == 0


@pytest.mark.django_db
def test_start_from_here_excludes_earlier_turns():
    user = get_user_model().objects.create_user("cull-here", password="pw")
    cid = "conv-start-here"
    messages = _turns(
        ("user", "drop-one"),
        ("assistant", "drop-two"),
        ("user", "keep-three"),
        ("assistant", "keep-four"),
    )
    _seed_json(user, "codey", messages, cid)
    result = preview_start_from_here(
        user=user,
        conversation_id=cid,
        agent_id="codey",
        messages=messages,
        start_offset=2,
        confirm=True,
        inference_entry={"context_length": 10_000},
    )
    assert result.acted is True
    assert result.warning is False
    assert result.start_offset == 2
    contents = [row.get("content") for row in result.context]
    assert contents == ["keep-three", "keep-four"]
    assert "drop-one" not in contents
    meta = load_context_meta(cid)
    assert meta["start_offset"] == 2
    assert meta["last_event"]["kind"] == EVENT_START_FROM_HERE


@pytest.mark.django_db
def test_start_from_here_warns_when_still_over_trigger():
    user = get_user_model().objects.create_user("cull-warn", password="pw")
    UserPreference.objects.create(
        user=user,
        principal="user:cull-warn",
        values={"context_strategy": "cull", "context_cull_trigger_pct": 50},
    )
    cid = "conv-start-warn"
    messages = _turns(
        ("user", "tiny"),
        ("assistant", "huge " * 80),
        ("user", "also-huge " * 80),
    )
    _seed_json(user, "jeeves", messages, cid)
    from swarm.core.context_compress_policy import estimate_context_tokens

    suffix = messages[1:]
    estimated = estimate_context_tokens(suffix)
    result = preview_start_from_here(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=messages,
        start_offset=1,
        confirm=False,
        inference_entry={"context_length": max(20, estimated)},
    )
    assert result.acted is False
    assert result.warning is True
    assert result.reason == "over_full_warning"
    assert result.info
    assert "Confirm" in result.info
    assert load_context_meta(cid)["start_offset"] == 0

    confirmed = preview_start_from_here(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=messages,
        start_offset=1,
        confirm=True,
        inference_entry={"context_length": max(20, estimated)},
    )
    assert confirmed.acted is True
    assert confirmed.warning is False
    assert load_context_meta(cid)["start_offset"] == 1


@pytest.mark.django_db
def test_context_start_endpoint_warning_and_confirm():
    user = get_user_model().objects.create_user("cull-api", password="pw")
    UserPreference.objects.create(
        user=user,
        principal="user:cull-api",
        values={"context_strategy": "cull", "context_cull_trigger_pct": 10},
    )
    from django.test import Client

    client = Client()
    client.login(username="cull-api", password="pw")
    cid = "conv-api-start"
    messages = _turns(
        ("user", "before " * 40),
        ("assistant", "after " * 40),
    )
    _seed_json(user, "jeeves", messages, cid)
    from swarm.core.context_compress_policy import estimate_context_tokens

    estimated = estimate_context_tokens(messages[1:])
    warn = client.post(
        "/chat/context-start/",
        data={
            "conversation_id": cid,
            "agent": "jeeves",
            "messages": messages,
            "start_offset": 1,
            "confirm": False,
            "context_length": max(10, estimated),
        },
        content_type="application/json",
    )
    assert warn.status_code == 200
    assert warn.json()["warning"] is True
    assert warn.json()["applied"] is False
    assert load_context_meta(cid)["start_offset"] == 0
    posted = client.post(
        "/chat/context-start/",
        data={
            "conversation_id": cid,
            "agent": "jeeves",
            "messages": messages,
            "start_offset": 1,
            "confirm": True,
        },
        content_type="application/json",
    )
    assert posted.status_code == 200
    body = posted.json()
    assert body["applied"] is True
    assert body["start_offset"] == 1
    assert [row.get("content") for row in body["context"]] == [messages[1]["content"]]
    assert "sk-" not in str(body)


@pytest.mark.django_db
def test_prepare_dispatches_cull_not_compress():
    user = get_user_model().objects.create_user("cull-prep", password="pw")
    UserPreference.objects.create(
        user=user,
        principal="user:cull-prep",
        values={
            "context_strategy": "cull",
            "context_cull_trigger_pct": 50,
            "context_cull_fraction_pct": 50,
        },
    )
    cid = "conv-prep-cull"
    messages = _turns(
        ("user", "aaaa " * 80),
        ("assistant", "bbbb " * 80),
        ("user", "cccc " * 80),
        ("assistant", "dddd " * 80),
    )
    _seed_json(user, "jeeves", messages, cid)
    from swarm.core.context_compress_policy import estimate_context_tokens
    from swarm.models import ConversationSummary

    estimated = estimate_context_tokens(messages)
    result = prepare_context_before_send(
        user=user,
        conversation_id=cid,
        agent_id="jeeves",
        messages=messages,
        inference_entry={"context_length": max(20, estimated)},
    )
    assert result.strategy == "cull"
    assert result.acted is True
    assert ConversationSummary.objects.filter(conversation_id=cid).count() == 0
    assert result.start_offset > 0
