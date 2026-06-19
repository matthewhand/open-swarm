"""File-backed store for the OpenAI Responses API statefulness.

The Responses API is *stateful*: a response is persisted (unless ``store: false``)
and a later request can pass ``previous_response_id`` to continue the
conversation. We persist each response as one JSON file on disk — no DB
migration, and the store dir is configurable (``SWARM_RESPONSES_DIR``).

Each record holds the public ``response`` payload (for ``GET /v1/responses/{id}``)
plus the full ``messages`` transcript that produced it (input + the assistant
reply) so a follow-up ``previous_response_id`` can replay the conversation.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

# resp ids we mint look like ``resp_<uuid>``; restrict to a safe charset so a
# caller-supplied id can never traverse out of the store dir.
_ID_RE = re.compile(r"^resp_[A-Za-z0-9_-]{1,128}$")


def _store_dir() -> Path:
    """Where response records live: ``$SWARM_RESPONSES_DIR`` or an XDG default."""
    env = os.environ.get("SWARM_RESPONSES_DIR")
    if env:
        return Path(env)
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "swarm" / "responses"


def _path_for(response_id: str, base_dir: Path | None) -> Path | None:
    if not _ID_RE.match(response_id or ""):
        return None
    return (base_dir or _store_dir()) / f"{response_id}.json"


def save(record: dict[str, Any], *, base_dir: Path | None = None) -> None:
    """Persist a record (must have a valid ``id``). Atomic write; best-effort."""
    rid = record.get("id", "")
    path = _path_for(rid, base_dir)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # write to a temp file in the same dir, then atomic rename.
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(record, f, default=str)
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def load(response_id: str, *, base_dir: Path | None = None) -> dict[str, Any] | None:
    """Return the stored record for ``response_id``, or None if absent/invalid."""
    path = _path_for(response_id, base_dir)
    if path is None or not path.is_file():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def list_summaries(*, base_dir: Path | None = None, limit: int | None = 200) -> list[dict[str, Any]]:
    """Lightweight summaries of stored sessions, newest first.

    Each summary: ``{id, model, status, created_at, execution_ms, output_preview,
    delegations}`` where ``delegations`` is the per-role progress array (possibly
    empty). Used by the Session Explorer web UI; reads each record once.
    """
    base = base_dir or _store_dir()
    if not base.is_dir():
        return []
    summaries: list[dict[str, Any]] = []
    for path in base.glob("resp_*.json"):
        try:
            with open(path) as f:
                record = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        resp = record.get("response") or {}
        text = resp.get("output_text") or ""
        summaries.append({
            "id": resp.get("id") or record.get("id"),
            "model": resp.get("model"),
            "status": resp.get("status"),
            "created_at": resp.get("created_at") or resp.get("started_at") or 0,
            "execution_ms": resp.get("execution_ms"),
            "output_preview": (text[:160] + "…") if len(text) > 160 else text,
            "delegations": resp.get("progress") or [],
        })
    summaries.sort(key=lambda s: s.get("created_at") or 0, reverse=True)
    return summaries[:limit] if limit else summaries


def delete(response_id: str, *, base_dir: Path | None = None) -> bool:
    """Delete the stored record; True if one was removed."""
    path = _path_for(response_id, base_dir)
    if path is None or not path.is_file():
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False
