"""async_retry: retry transient (5xx) failures, fail fast on 4xx client errors."""
from __future__ import annotations

import pytest
from rest_framework.exceptions import APIException, NotFound, ParseError, PermissionDenied

from swarm.views.responses_views import async_retry


@pytest.mark.parametrize("exc", [ParseError, PermissionDenied, NotFound])
async def test_4xx_client_errors_are_not_retried(exc):
    calls = {"n": 0}

    @async_retry(max_attempts=3, base_delay=0)
    async def f():
        calls["n"] += 1
        raise exc("nope")

    with pytest.raises(exc):
        await f()
    assert calls["n"] == 1  # failed fast, no backoff retries


async def test_5xx_is_retried_then_succeeds():
    calls = {"n": 0}

    @async_retry(max_attempts=3, base_delay=0)
    async def f():
        calls["n"] += 1
        if calls["n"] < 2:
            raise APIException("transient 500")  # status_code 500
        return "ok"

    assert await f() == "ok"
    assert calls["n"] == 2


async def test_retries_exhaust_then_reraise():
    calls = {"n": 0}

    @async_retry(max_attempts=3, base_delay=0)
    async def f():
        calls["n"] += 1
        raise APIException("always 500")

    with pytest.raises(APIException):
        await f()
    assert calls["n"] == 3
