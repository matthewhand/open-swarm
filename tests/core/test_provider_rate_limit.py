"""REQ-88 / #445 — shared provider rate-limit queue (no live paid provider)."""

from __future__ import annotations

import json

import pytest

from swarm.core.provider_rate_limit import (
    ProviderRateLimiter,
    RateLimitRules,
    format_cli_wait,
    format_wait_text,
    gate_provider_send,
    infer_provider_key,
    load_rules,
    parse_rules,
    persist_provider_rate_limits,
    reset_limiter,
    resolve_provider_key,
    settings_target,
)
from swarm.core.transcript_roles import context_blob, messages_for_model


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def now(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.t += max(0.0, float(seconds))


def _limiter(clock: FakeClock | None = None) -> ProviderRateLimiter:
    clock = clock or FakeClock()
    return ProviderRateLimiter(now=clock.now, sleep=clock.sleep, minute_window=60.0, day_window=86400.0)


def test_empty_rules_are_unlimited():
    assert parse_rules({}).is_unlimited()
    assert parse_rules({"messages_per_minute": ""}).is_unlimited()
    assert parse_rules({"messages_per_minute": 0}).is_unlimited()
    assert parse_rules({"messages_per_minute": None}).is_unlimited()
    assert not parse_rules({"messages_per_minute": 1}).is_unlimited()


def test_no_baked_vendor_defaults():
    raw = json.dumps(RateLimitRules().public_dict())
    assert "5" not in raw
    assert all(value is None for value in RateLimitRules().public_dict().values())


@pytest.mark.asyncio
async def test_two_agents_one_provider_second_waits():
    clock = FakeClock()
    limiter = _limiter(clock)
    rules = RateLimitRules(messages_per_minute=1)
    first = await limiter.acquire("cli:stub", rules, messages=1, requests=1)
    assert first is None
    waits: list[str] = []

    async def on_wait(decision):
        waits.append(decision.rule)

    second = await limiter.acquire("cli:stub", rules, messages=1, requests=1, on_wait=on_wait)
    assert second is not None
    assert second.rule == "messages_per_minute"
    assert second.remaining_seconds > 0
    assert waits and waits[0] == "messages_per_minute"
    assert clock.t > 1000.0


@pytest.mark.asyncio
async def test_two_providers_do_not_share_a_queue():
    limiter = _limiter()
    rules = RateLimitRules(messages_per_minute=1)
    assert await limiter.acquire("cli:alpha", rules) is None
    assert await limiter.acquire("cli:beta", rules) is None
    blocked = limiter.inspect("cli:alpha", rules, messages=1, requests=1)
    assert blocked is not None
    assert limiter.inspect("cli:beta", rules, messages=1, requests=1) is not None


def test_settings_target_points_at_that_provider():
    target = settings_target("cli:grok")
    assert target["section"] == "cli-agents"
    assert target["provider_id"] == "cli:grok"
    assert target["field_id"] == "rate-limits-cli-grok"
    assert target["focus"] == "rate-limits"
    assert settings_target("llm:local")["section"] == "llm-profiles"
    assert settings_target("remote:hermes")["section"] == "remotes"


def test_wait_copy_names_rule_and_countdown():
    limiter = _limiter()
    limiter.record("cli:grok", messages=1)
    decision = limiter.inspect("cli:grok", RateLimitRules(messages_per_minute=1), messages=1)
    assert decision is not None
    text = format_wait_text(decision)
    assert "grok" in text
    assert "messages per minute" in text
    assert "s" in text
    assert "Django" not in text
    cli = format_cli_wait(decision)
    assert "reason=messages_per_minute" in cli
    assert "remaining_seconds=" in cli


def test_persist_and_load_on_provider_row(tmp_path, monkeypatch):
    path = tmp_path / "swarm_config.json"
    path.write_text(json.dumps({"llm": {}, "cli_agents": {"stub": {"cmd": ["echo"]}}}), encoding="utf-8")
    parsed, written = persist_provider_rate_limits(
        "cli:stub",
        {"messages_per_minute": 1, "tokens_per_minute": 100},
        config_path=path,
    )
    assert written == path
    assert parsed.messages_per_minute == 1
    assert parsed.tokens_per_minute == 100
    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob["cli_agents"]["stub"]["cmd"] == ["echo"]
    assert blob["cli_agents"]["stub"]["rate_limits"]["messages_per_minute"] == 1
    assert "Django" not in path.read_text(encoding="utf-8")
    loaded = load_rules("cli:stub", config_path=path)
    assert loaded.messages_per_minute == 1
    persist_provider_rate_limits("cli:stub", {}, config_path=path)
    assert load_rules("cli:stub", config_path=path).is_unlimited()


def test_resolve_provider_key_from_inference_and_cli():
    assert resolve_provider_key(params={"inference_list": ["cli:grok"]}) == "cli:grok"
    assert resolve_provider_key(params={"cli": "agy"}) == "cli:agy"
    assert resolve_provider_key(params={"remote_id": "hermes"}) == "remote:hermes"
    assert infer_provider_key("local", {"llm": {"local": {"model": "x"}}}) == "llm:local"


@pytest.mark.asyncio
async def test_gate_skips_unlimited_and_records_limited(tmp_path):
    path = tmp_path / "swarm_config.json"
    path.write_text(
        json.dumps({"llm": {}, "cli_agents": {"stub": {"cmd": ["echo"], "rate_limits": {"messages_per_minute": 1}}}}),
        encoding="utf-8",
    )
    clock = FakeClock()
    limiter = reset_limiter(_limiter(clock))
    cfg = json.loads(path.read_text(encoding="utf-8"))
    first = await gate_provider_send(params={"cli": "stub"}, config=cfg, limiter=limiter)
    assert first is None
    second = await gate_provider_send(params={"cli": "stub"}, config=cfg, limiter=limiter)
    assert second is not None
    assert second.rule == "messages_per_minute"
    reset_limiter()


def test_countdown_info_is_not_in_model_prompt():
    text = "Waiting for stub — messages per minute — 12s"
    thread = [
        {"role": "info", "kind": "rate_limit", "content": text, "rate_limit": {"reason": "messages_per_minute"}},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    payload = messages_for_model(thread)
    blob = context_blob(payload)
    assert text not in blob
    assert "messages per minute" not in blob
    assert [row["role"] for row in payload] == ["user", "assistant"]

