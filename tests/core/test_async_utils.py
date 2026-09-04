"""run_coro_sync: no get_event_loop, works with and without a running loop."""

import asyncio

from swarm.core.async_utils import run_coro_sync


async def _one() -> int:
    return 1


def test_run_coro_sync_without_running_loop():
    assert run_coro_sync(_one()) == 1


def test_run_coro_sync_inside_running_loop():
    async def _nested() -> int:
        return run_coro_sync(_one())

    assert asyncio.run(_nested()) == 1
