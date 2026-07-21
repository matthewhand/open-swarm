"""Process-local in-flight concurrency limits for blueprint execution.

Single-instance only — not a multi-worker distributed semaphore. Used to
reject overload with a client-safe 429 instead of unbounded thread growth.

Until a shared queue exists, async ``/v1/responses`` cancel + inflight are
**per process**. Prefer a single uvicorn worker (``SWARM_UVICORN_WORKERS=1``).
"""
from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_inflight = 0


def resolved_uvicorn_workers() -> int:
    """Resolve uvicorn worker count; warn or refuse multi-worker async.

    Default 1. When ``SWARM_ENFORCE_SINGLE_WORKER`` is true (default), values
    greater than 1 raise ``ValueError`` so operators cannot silently break
    cancel/inflight. Set the env to false to allow multi-worker with a warning.
    """
    raw = os.getenv("SWARM_UVICORN_WORKERS", "1") or "1"
    try:
        n = int(raw)
    except ValueError:
        n = 1
    n = max(1, n)
    enforce = os.getenv("SWARM_ENFORCE_SINGLE_WORKER", "true").lower() in (
        "true", "1", "yes", "y", "t",
    )
    if n > 1:
        msg = (
            f"SWARM_UVICORN_WORKERS={n} > 1: /v1/responses cancel and inflight "
            "limits are process-local until a shared queue exists. Prefer workers=1."
        )
        if enforce:
            raise ValueError(msg + " Set SWARM_ENFORCE_SINGLE_WORKER=false to override.")
        logger.warning(msg)
    return n


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
