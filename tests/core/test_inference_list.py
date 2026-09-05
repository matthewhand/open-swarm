"""REQ-69 ordered inference helpers."""

from swarm.core.inference_list import (
    failover_notice,
    is_config_failure,
    is_rate_limit,
    normalize_inference_list,
    pick_scale_out,
    seat_id,
    seat_kind,
)


def test_normalize_preserves_order_and_dedupes():
    assert normalize_inference_list(["llm:orchestration", "cli:grok", "llm:orchestration"]) == [
        "llm:orchestration",
        "cli:grok",
    ]
    assert normalize_inference_list(None) == []
    assert normalize_inference_list([{"kind": "cli", "id": "agy"}]) == ["cli:agy"]


def test_empty_list_is_settings_default():
    assert normalize_inference_list([]) == []
    assert pick_scale_out([], 0) is None


def test_scale_out_round_robin_two_tasks_two_providers():
    seats = ["llm:a", "llm:b"]
    assert pick_scale_out(seats, 0) == "llm:a"
    assert pick_scale_out(seats, 1) == "llm:b"
    assert pick_scale_out(seats, 2) == "llm:a"


def test_config_fail_is_not_rate_limit():
    class MissingKey(Exception):
        pass

    class Rate(Exception):
        status_code = 429

    class Auth(Exception):
        status_code = 401

    assert is_config_failure(MissingKey("API key not set for grok"))
    assert is_config_failure(Auth("unauthorized"))
    assert not is_rate_limit(Auth("unauthorized"))
    assert is_rate_limit(Rate("too many requests"))
    assert not is_config_failure(Rate("429 rate limit"))


def test_should_failover_and_retry_params():
    from swarm.core.inference_list import retry_params, should_failover

    class Missing(Exception):
        pass

    class Rate(Exception):
        status_code = 429

    seats = ["llm:a", "llm:b"]
    assert should_failover(Missing("unknown model"), seats[1:], scale_out=False)
    assert not should_failover(Missing("unknown model"), seats[1:], scale_out=True)
    assert not should_failover(Rate("429"), seats[1:], scale_out=False)
    retry = retry_params({"inference_list": seats}, ["llm:b"])
    assert retry["inference_list"] == ["llm:b"]
    assert retry["llm_profile"] == "b"


def test_429_does_not_jump():
    class Rate(Exception):
        status_code = 429

    assert is_rate_limit(Rate("429"))
    assert not is_config_failure(Rate("429"))


def test_failover_notice_exhausted():
    assert "Trying llm:b" in failover_notice("llm:a", "llm:b")
    assert "exhausted" in failover_notice("llm:b", None, exhausted=True).lower()


def test_seat_kind_and_id():
    assert seat_kind("cli:grok") == "cli"
    assert seat_id("cli:grok") == "grok"
    assert seat_kind("orchestration") == "llm"
    assert seat_id("llm:auxiliary") == "auxiliary"
