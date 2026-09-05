"""REQ-69: consumer uses should_failover so 429 stays put."""

from swarm.core.inference_list import should_failover


class _ConfigFail(Exception):
    status_code = 401


class _RateLimit(Exception):
    status_code = 429


def test_config_fail_walks_to_second():
    rest = ["llm:b"]
    assert should_failover(_ConfigFail("missing api key"), rest, scale_out=False)


def test_429_on_first_does_not_jump_to_second():
    rest = ["llm:b"]
    assert not should_failover(_RateLimit("429 rate limit"), rest, scale_out=False)
    assert not should_failover(_ConfigFail("missing api key"), rest, scale_out=True)
