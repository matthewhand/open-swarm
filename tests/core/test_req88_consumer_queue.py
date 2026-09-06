"""REQ-88: two stub agents share one provider queue; chrome stays off the model."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from swarm.core.provider_rate_limit import (
    ProviderRateLimiter,
    reset_limiter,
)
from swarm.core.transcript_roles import context_blob, messages_for_model
from swarm.consumers import DjangoChatConsumer


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.t += max(0.0, float(seconds))


def _consumer() -> DjangoChatConsumer:
    consumer = DjangoChatConsumer()
    consumer.messages = []
    consumer.ui_events = []
    consumer.user = MagicMock()
    consumer.user.is_authenticated = True
    consumer.conversation_id = "req88-conv"
    consumer.send = AsyncMock()
    consumer.send_error_message = AsyncMock()
    consumer._persist_completed_turn = AsyncMock()
    consumer._emit_suggestions_if_enabled = AsyncMock()
    return consumer


@pytest.fixture
def limited_stub(tmp_path, monkeypatch):
    path = tmp_path / "swarm_config.json"
    path.write_text(
        json.dumps(
            {
                "llm": {},
                "cli_agents": {
                    "stub": {"cmd": ["echo"], "rate_limits": {"messages_per_minute": 1}}
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("SWARM_CONFIG_PATH", str(path))
    clock = FakeClock()
    limiter = reset_limiter(
        ProviderRateLimiter(now=clock.now, sleep=clock.sleep, minute_window=60.0)
    )
    yield limiter, clock
    reset_limiter()


@pytest.mark.asyncio
async def test_two_stub_agents_one_provider_second_waits(limited_stub):
    _limiter, _clock = limited_stub
    first = _consumer()
    first.messages = [{"role": "user", "content": "alpha"}]
    second = _consumer()
    second.messages = [{"role": "user", "content": "beta"}]
    params = {"cli": "stub"}

    await first.respond_with_blueprint("jeeves", "message-response-a", params=params)
    await second.respond_with_blueprint("chatbot", "message-response-b", params=params)

    events = second.ui_events
    rate = [row for row in events if row.get("kind") == "rate_limit" or row.get("role") == "info"]
    assert rate, events
    assert "messages per minute" in rate[0]["content"]
    assert "stub" in rate[0]["content"]
    assert rate[0]["rate_limit"]["reason"] == "messages_per_minute"
    assert rate[0]["rate_limit"]["remaining_seconds"] > 0
    frames = [
        call.kwargs.get("text_data") or (call.args[0] if call.args else "")
        for call in second.send.await_args_list
    ]
    html = "\n".join(str(frame) for frame in frames)
    assert "os-chat-status--rate-limit" in html
    assert 'data-provider="cli:stub"' in html


@pytest.mark.asyncio
async def test_two_providers_independent(limited_stub):
    await _consumer().respond_with_blueprint("jeeves", "a", params={"cli": "stub"})
    other = _consumer()
    other.messages = [{"role": "user", "content": "ok"}]
    await other.respond_with_blueprint("chatbot", "b", params={"cli": "other"})
    assert not any(row.get("kind") == "rate_limit" for row in other.ui_events)


@pytest.mark.asyncio
async def test_rate_limit_info_not_in_model_prompt(limited_stub):
    first = _consumer()
    first.messages = [{"role": "user", "content": "one"}]
    await first.respond_with_blueprint("jeeves", "a", params={"cli": "stub"})
    second = _consumer()
    second.messages = [{"role": "user", "content": "two"}]
    await second.respond_with_blueprint("chatbot", "b", params={"cli": "stub"})
    payload = messages_for_model(second.messages + second.ui_events)
    blob = context_blob(payload)
    assert "Waiting for" not in blob
    assert "messages per minute" not in blob
    assert all(row.get("role") in {"user", "assistant", "system", "tool", "developer"} for row in payload)


def test_wait_html_is_not_a_model_bubble():
    from swarm.consumers import _rate_limit_status_html

    html = _rate_limit_status_html(
        "Waiting for stub — messages per minute — 9s",
        {
            "provider": "cli:stub",
            "reason": "messages_per_minute",
            "remaining_seconds": 9,
            "settings": {"field_id": "rate-limits-cli-stub"},
        },
    )
    assert "chat-start" not in html
    assert "assistant-message" not in html
    assert "os-chat-status" in html
    assert "Django" not in html
