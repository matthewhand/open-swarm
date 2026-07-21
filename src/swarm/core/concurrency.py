"""Process-local in-flight concurrency limits for blueprint execution.

Single-instance only — not a multi-worker distributed semaphore. Used to
reject overload with a client-safe 429 instead of unbounded thread growth.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

_lock = threading.Lock()
_inflight = 0


def max_inflight() -> int:
    try:
        from django.conf import settings
        return int(getattr(settings, "SWARM_MAX_INFLIGHT", 8))
    except Exception:
        import os
        return int(os.getenv("SWARM_MAX_INFLIGHT", "8"))


def current_inflight() -> int:
    with _lock:
        return _inflight


def try_acquire() -> bool:
    """Atomically take one slot if under the limit. Returns False if full."""
    global _inflight
    limit = max_inflight()
    with _lock:
        if _inflight >= limit:
            return False
        _inflight += 1
        return True


def release() -> None:
    global _inflight
    with _lock:
        _inflight = max(0, _inflight - 1)


@contextmanager
def inflight_slot():
    """Context manager: acquire or raise RuntimeError if pool is full."""
    if not try_acquire():
        raise RuntimeError(
            f"Too many in-flight requests (limit={max_inflight()}). Retry later."
        )
    try:
        yield
    finally:
        release()
