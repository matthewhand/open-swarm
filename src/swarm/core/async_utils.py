"""Sync helpers for awaiting openai-agents tools without deprecated loop APIs."""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run_coro_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run *coro* from sync code on 3.10–3.12 without ``get_event_loop()``.

    * No running loop → ``asyncio.run``.
    * Already inside a loop → run in a worker thread (nested ``asyncio.run``).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
