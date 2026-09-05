"""Provider-owned session stores (ids + display metadata only).

Used when a CLI has no official non-interactive list argv but still owns
sessions on disk. Open Swarm does **not** invent a parallel session DB —
we only enumerate the CLI's own files. Never open secret-shaped payloads
(agy conversation sqlite is protobuf; we use filename stem + mtime only).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from swarm.core.cli_catalog import AGY_CONVERSATIONS_STORE
from swarm.core.cli_sessions import sanitize_cli_session_id

logger = logging.getLogger(__name__)


def list_store_sessions(kind: str, store_dir: str | Path | None) -> list[dict[str, Any]]:
    """Enumerate one provider store. Unknown kind → empty (no fake rows)."""
    if kind == AGY_CONVERSATIONS_STORE:
        return list_agy_conversations(store_dir)
    logger.warning("Unknown CLI session store %r — not listing", kind)
    return []


def list_agy_conversations(store_dir: str | Path | None) -> list[dict[str, Any]]:
    """List agy conversation ids from ``<dir>/<uuid>.db`` stems.

    The stem is the id passed to ``agy --conversation``. Display metadata is
    the id plus file mtime. The sqlite is never opened.
    """
    if not store_dir:
        return []
    root = Path(store_dir)
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    try:
        entries = list(root.iterdir())
    except OSError:
        logger.warning("Could not read agy conversations dir %s", root)
        return []
    for path in entries:
        if not path.is_file() or path.suffix != ".db":
            continue
        sid = sanitize_cli_session_id(path.stem)
        if not sid:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        updated = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        rows.append(
            {
                "id": sid,
                "title": sid,
                "snippet": "",
                "updated_at": updated,
                "source": "provider",
            }
        )
    rows.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    return rows
