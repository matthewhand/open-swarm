"""Herdr as a remotes kind (REQ-64).

Settings + ``swarm-cli remotes`` persist ``remotes.herdr`` (base URL +
api-key-env). That is **opt-in**: there is no baked LAN host. Missing config
is a clear error, not a silent other-host.

``herdr --remote`` / ``HerdrClient.from_remote_config`` use that configured
base. Localhost (loopback) omits the flag — the documented default — only when
the user set a localhost URL.

HTTP health/list talk to the configured base (``GET /health``, ``GET /agents``).
Tests stub that HTTP. Do not point CI at a live LAN Herdr.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from swarm.herdr.client import members_from_agent_list, members_from_workspace_list

KIND_ID = "herdr"
HEALTH_PATH = "/health"
LIST_PATH = "/agents"
API_KEY_ENV = "HERDR_API_KEY"
BASE_URL_ENV = "HERDR_BASE_URL"

_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})

HERDR_NOT_CONFIGURED = (
    "Herdr remote is not configured. Add kind=herdr in Settings "
    "(base URL + api-key-env name) or run: swarm-cli remotes set herdr "
    "--base-url <url> --api-key-env HERDR_API_KEY. "
    "Refusing to guess another host."
)


def not_configured_message() -> str:
    return HERDR_NOT_CONFIGURED


def is_localhost_base(base_url: str) -> bool:
    """True when the user configured a loopback base (omit ``herdr --remote``)."""
    raw = (base_url or "").strip()
    if not raw:
        return False
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = (parsed.hostname or "").strip().lower()
    return host in _LOCAL_HOSTS


def cli_remote_from_base(base_url: str) -> str:
    """Value for ``herdr --remote``. Empty means localhost (omit the flag).

    Raises ``ValueError`` when *base_url* is missing so callers cannot silently
    fall through to another host.
    """
    raw = (base_url or "").strip()
    if not raw:
        raise ValueError(HERDR_NOT_CONFIGURED)
    if is_localhost_base(raw):
        return ""
    return raw.rstrip("/")


def members_from_http_list(payload: Any, *, remote: str = "") -> list[dict[str, Any]]:
    """Map a stub/HTTP list body onto addable ``kind=herdr`` members."""
    if isinstance(payload, dict):
        if payload.get("agents") is not None or (
            isinstance(payload.get("result"), dict) and "agents" in payload["result"]
        ):
            found = members_from_agent_list(payload, remote=remote)
            if found:
                return found
        if payload.get("workspaces") is not None or (
            isinstance(payload.get("result"), dict) and "workspaces" in payload["result"]
        ):
            found = members_from_workspace_list(payload, remote=remote)
            if found:
                return found
        inner = payload.get("data") or payload.get("items") or payload.get("members")
        if inner is not None and inner is not payload:
            found = members_from_http_list(inner, remote=remote)
            if found:
                return found
    if isinstance(payload, list):
        as_agents = members_from_agent_list(payload, remote=remote)
        if as_agents:
            return as_agents
        return members_from_workspace_list({"workspaces": payload}, remote=remote)
    return []
