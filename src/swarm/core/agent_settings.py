"""Per-agent settings store (REQ-65).

File-backed JSON so the SPA editor, CoS handoffs, API session create, and
CLI/remote resume gates share one source of truth. Default is reuse (off).

Layout::

    <user-config>/agent_settings.json

    {
      "schema": 1,
      "agents": {
        "<agent_id>": {
          "new_chat_per_task": false,
          "cli_session_id": null,
          "remote_session_id": null
        }
      }
    }

This is **not** global Settings (Remotes / Retention / Hostname). Agent-scoped
only — see the SPA ``AgentEditorSheet``.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from swarm.core.chat_store import normalize_agent_id
from swarm.core.paths import ensure_swarm_directories_exist, get_user_config_dir_for_swarm

logger = logging.getLogger(__name__)

SCHEMA = 1
ENV_SETTINGS_PATH = "SWARM_AGENT_SETTINGS_PATH"
KEY_NEW_CHAT_PER_TASK = "new_chat_per_task"
KEY_CLI_SESSION = "cli_session_id"
KEY_REMOTE_SESSION = "remote_session_id"

DEFAULTS: dict[str, Any] = {
    KEY_NEW_CHAT_PER_TASK: False,
    KEY_CLI_SESSION: None,
    KEY_REMOTE_SESSION: None,
}

_ALLOWED_KEYS = frozenset(DEFAULTS)
_BOOL_KEYS = frozenset({KEY_NEW_CHAT_PER_TASK})
_ID_KEYS = frozenset({KEY_CLI_SESSION, KEY_REMOTE_SESSION})

_cache: dict[str, Any] | None = None


def settings_path() -> Path:
    """Path of the agent-settings JSON file."""
    env = (os.environ.get(ENV_SETTINGS_PATH) or "").strip()
    if env:
        return Path(env)
    ensure_swarm_directories_exist()
    return get_user_config_dir_for_swarm() / "agent_settings.json"


def reset_agent_settings_cache() -> None:
    """Drop the in-process cache (tests)."""
    global _cache
    _cache = None


def _empty_store() -> dict[str, Any]:
    return {"schema": SCHEMA, "agents": {}}


def _read_store() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    path = settings_path()
    if not path.is_file():
        _cache = _empty_store()
        return _cache
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read agent settings at %s", path, exc_info=True)
        _cache = _empty_store()
        return _cache
    if not isinstance(data, dict):
        _cache = _empty_store()
        return _cache
    agents = data.get("agents")
    if not isinstance(agents, dict):
        agents = {}
    _cache = {"schema": SCHEMA, "agents": dict(agents)}
    return _cache


def _write_store(store: dict[str, Any]) -> None:
    global _cache
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": SCHEMA, "agents": store.get("agents") or {}}
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)
            handle.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _cache = payload


def _normalize_value(key: str, value: Any) -> Any:
    if key in _BOOL_KEYS:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "1", "yes", "on"):
                return True
            if lowered in ("false", "0", "no", "off", ""):
                return False
        raise ValueError(f"{key} must be a boolean.")
    if key in _ID_KEYS:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
    return value


def public_settings(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    """Stable JSON shape for the editor / API."""
    merged = dict(DEFAULTS)
    if isinstance(raw, dict):
        for key in _ALLOWED_KEYS:
            if key in raw:
                try:
                    merged[key] = _normalize_value(key, raw[key])
                except ValueError:
                    continue
    return {
        KEY_NEW_CHAT_PER_TASK: bool(merged[KEY_NEW_CHAT_PER_TASK]),
        KEY_CLI_SESSION: merged[KEY_CLI_SESSION],
        KEY_REMOTE_SESSION: merged[KEY_REMOTE_SESSION],
    }


def get_settings(agent_id: str) -> dict[str, Any]:
    """Return settings for one agent. Missing agents get defaults (toggle off)."""
    agent = normalize_agent_id(agent_id)
    store = _read_store()
    raw = store["agents"].get(agent)
    return public_settings(raw if isinstance(raw, dict) else None)


def update_settings(agent_id: str, patch: dict[str, Any] | None) -> dict[str, Any]:
    """Merge ``patch`` into one agent's settings and persist."""
    agent = normalize_agent_id(agent_id)
    incoming = patch if isinstance(patch, dict) else {}
    unknown = [key for key in incoming if key not in _ALLOWED_KEYS]
    if unknown:
        raise ValueError(f"Unknown agent setting(s): {', '.join(sorted(unknown))}.")
    current = get_settings(agent)
    for key, value in incoming.items():
        current[key] = _normalize_value(key, value)
    store = _read_store()
    agents = dict(store.get("agents") or {})
    agents[agent] = current
    _write_store({"schema": SCHEMA, "agents": agents})
    return dict(current)


def is_new_chat_per_task(agent_id: str | None) -> bool:
    """True when this agent starts a fresh session per task (default False)."""
    if not (agent_id or "").strip():
        return False
    return bool(get_settings(agent_id)[KEY_NEW_CHAT_PER_TASK])


def stored_cli_session_id(agent_id: str) -> str | None:
    value = get_settings(agent_id).get(KEY_CLI_SESSION)
    return str(value) if value else None


def stored_remote_session_id(agent_id: str) -> str | None:
    value = get_settings(agent_id).get(KEY_REMOTE_SESSION)
    return str(value) if value else None


def set_cli_session_id(agent_id: str, session_id: str | None) -> dict[str, Any]:
    return update_settings(agent_id, {KEY_CLI_SESSION: session_id})


def set_remote_session_id(agent_id: str, session_id: str | None) -> dict[str, Any]:
    return update_settings(agent_id, {KEY_REMOTE_SESSION: session_id})
