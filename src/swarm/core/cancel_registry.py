"""File-backed cancel registry for ``/v1/responses``.

Cooperative cancel flags live under ``{SWARM_RESPONSES_DIR}/cancel/{id}.flag``
so multiple uvicorn workers that share the same filesystem can cancel each
other's jobs. A process-local set is kept as a fast path for same-worker
checks; the filesystem is always written and is the cross-worker source of
truth.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path

from swarm.core.responses_store import _store_dir

# Same charset as responses_store — reject path-traversal / junk ids.
_ID_RE = re.compile(r"^resp_[A-Za-z0-9_-]{1,128}$")

_local: set[str] = set()
_local_lock = threading.Lock()


def _cancel_dir(base_dir: Path | None = None) -> Path:
    return (base_dir or _store_dir()) / "cancel"


def _flag_path(response_id: str, base_dir: Path | None = None) -> Path | None:
    if not _ID_RE.match(response_id or ""):
        return None
    return _cancel_dir(base_dir) / f"{response_id}.flag"


def request_cancel(response_id: str, *, base_dir: Path | None = None) -> bool:
    """Request cooperative cancel for ``response_id``.

    Writes a flag under the responses store and warms the process-local set.
    Returns ``False`` if the id is invalid (no file written).
    """
    path = _flag_path(response_id, base_dir)
    if path is None:
        return False
    with _local_lock:
        _local.add(response_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Empty flag file; presence alone is the signal.
        path.write_text("", encoding="utf-8")
    except OSError:
        # Local set still marks cancel for this process; peer workers will
        # miss it until a later successful write (best-effort).
        pass
    return True


def is_cancel_requested(response_id: str, *, base_dir: Path | None = None) -> bool:
    """True if cancel was requested (local fast path or shared flag file)."""
    if not _ID_RE.match(response_id or ""):
        return False
    with _local_lock:
        if response_id in _local:
            return True
    path = _flag_path(response_id, base_dir)
    if path is None:
        return False
    try:
        if path.is_file():
            with _local_lock:
                _local.add(response_id)
            return True
    except OSError:
        return False
    return False


def clear_cancel(response_id: str, *, base_dir: Path | None = None) -> None:
    """Clear cancel flag for ``response_id`` (local + filesystem). Safe no-op on bad ids."""
    if not _ID_RE.match(response_id or ""):
        return
    with _local_lock:
        _local.discard(response_id)
    path = _flag_path(response_id, base_dir)
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
