"""Decouple a blueprint's *tool needs* from concrete providers.

A blueprint declares an abstract **capability** it needs — and whether it is
mandatory or optional — instead of naming a specific MCP server:

    tool_requirements = {"web_search": "mandatory", "filesystem": "optional"}

Each configured MCP server declares which capabilities it **provides** (via a
``provides`` list in its config, or a catalog default for known servers). The
resolver then maps each required capability to a usable provider, **preferring
non-auth providers** so examples run out of the box. A mandatory capability with
no usable provider is reported as missing; an unmet optional one is simply
skipped.

This mirrors :mod:`swarm.core.inference_profile` (intent → backend) for tools
(capability → provider), keeping blueprints portable across hosts: a blueprint
says "I need web search", and runs against whatever search provider you have —
Brave if you configured it, a non-auth DuckDuckGo/fetch server if you didn't.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# A capability is just a string; these are the well-known ones we tag/suggest.
WEB_SEARCH = "web_search"
WEB_FETCH = "web_fetch"
FILESYSTEM = "filesystem"
GIT = "git"
TIME = "time"


@dataclass(frozen=True)
class McpServer:
    """A known MCP server: how to run it and what it provides."""

    name: str
    provides: tuple[str, ...]
    command: str
    args: tuple[str, ...]
    auth_env: tuple[str, ...] = ()  # required secrets; empty == non-auth
    note: str = ""

    @property
    def needs_auth(self) -> bool:
        return bool(self.auth_env)

    def to_config(self) -> dict[str, Any]:
        cfg: dict[str, Any] = {
            "command": self.command,
            "args": list(self.args),
            "provides": list(self.provides),
        }
        if self.auth_env:
            cfg["env"] = {k: f"${{{k}}}" for k in self.auth_env}
        return cfg


# Catalog of known, runnable MCP servers. NON-AUTH servers come first for each
# capability so suggestions/resolution prefer them. Commands use npx/uvx so they
# need no prior install. Verify exact package names with the upstream registry.
CATALOG: tuple[McpServer, ...] = (
    # --- web search ---
    McpServer("duckduckgo", (WEB_SEARCH,), "uvx", ("duckduckgo-mcp-server",),
              note="Non-auth web search (community DuckDuckGo server)."),
    McpServer("brave-search", (WEB_SEARCH,), "npx",
              ("-y", "@modelcontextprotocol/server-brave-search"),
              auth_env=("BRAVE_API_KEY",), note="Brave Search — needs an API key."),
    # --- fetch a URL ---
    McpServer("fetch", (WEB_FETCH,), "uvx", ("mcp-server-fetch",),
              note="Non-auth: fetch and read a URL."),
    # --- local, non-auth utilities ---
    McpServer("filesystem", (FILESYSTEM,), "npx",
              ("-y", "@modelcontextprotocol/server-filesystem", "${ALLOWED_PATH}"),
              note="Non-auth local filesystem (scoped to ALLOWED_PATH)."),
    McpServer("git", (GIT,), "uvx", ("mcp-server-git",), note="Non-auth local git."),
    McpServer("time", (TIME,), "uvx", ("mcp-server-time",), note="Non-auth time/timezone."),
)

_BY_NAME = {s.name: s for s in CATALOG}


def known_server(name: str) -> McpServer | None:
    return _BY_NAME.get(name)


def servers_for(capability: str) -> list[McpServer]:
    """Known servers providing ``capability``, non-auth first then by name."""
    matches = [s for s in CATALOG if capability in s.provides]
    return sorted(matches, key=lambda s: (s.needs_auth, s.name))


def normalize_requirements(req: Any) -> dict[str, str]:
    """Coerce a blueprint's ``tool_requirements`` to ``{capability: level}``.

    Accepts a dict ``{cap: "mandatory"|"optional"}`` or a list/tuple of
    capabilities (treated as mandatory). Unknown levels default to mandatory.
    """
    if not req:
        return {}
    if isinstance(req, dict):
        return {
            str(k): ("optional" if str(v).lower() == "optional" else "mandatory")
            for k, v in req.items()
        }
    return {str(c): "mandatory" for c in req}


def _provider_capabilities(config: dict[str, Any] | None) -> dict[str, tuple[list[str], McpServer | None]]:
    """``{server_name: (capabilities, known_server_or_None)}`` from config.

    Capabilities come from the server's ``provides`` list, falling back to the
    catalog default for a known server name.
    """
    servers = (config or {}).get("mcpServers") or {}
    out: dict[str, tuple[list[str], McpServer | None]] = {}
    for name, entry in servers.items():
        known = known_server(name)
        provides = list((entry or {}).get("provides") or (known.provides if known else ()))
        out[name] = (provides, known)
    return out


def _usable(known: McpServer | None, env: dict[str, str]) -> bool:
    """A provider is usable if it needs no auth, or all its secrets are present."""
    if known is None or not known.needs_auth:
        return True
    return all(env.get(k) for k in known.auth_env)


@dataclass
class ToolResolution:
    satisfied: dict[str, str] = field(default_factory=dict)        # capability -> server name
    missing_mandatory: list[str] = field(default_factory=list)     # no usable provider
    skipped_optional: list[str] = field(default_factory=list)      # optional, no provider
    unusable: dict[str, str] = field(default_factory=dict)         # capability -> why (e.g. missing key)

    @property
    def ok(self) -> bool:
        return not self.missing_mandatory


def resolve_requirements(
    requirements: Any,
    config: dict[str, Any] | None,
    env: dict[str, str] | None = None,
) -> ToolResolution:
    """Map required capabilities to configured providers (non-auth preferred).

    For each capability, candidate providers are the configured ``mcpServers``
    that provide it; a usable one wins (non-auth first). Mandatory + none usable
    → ``missing_mandatory``; optional + none → ``skipped_optional``.
    """
    env = os.environ if env is None else env
    reqs = normalize_requirements(requirements)
    providers = _provider_capabilities(config)
    res = ToolResolution()

    for cap, level in reqs.items():
        candidates = [(n, known) for n, (caps, known) in providers.items() if cap in caps]
        # non-auth first, then by name, for deterministic preference
        candidates.sort(key=lambda nk: (nk[1].needs_auth if nk[1] else False, nk[0]))
        usable = [(n, k) for n, k in candidates if _usable(k, env)]
        if usable:
            res.satisfied[cap] = usable[0][0]
        elif candidates:
            # configured but not usable (e.g. auth key missing)
            n, k = candidates[0]
            missing = ", ".join(x for x in (k.auth_env if k else ())) or "auth"
            res.unusable[cap] = f"{n} needs {missing}"
            (res.missing_mandatory if level == "mandatory" else res.skipped_optional).append(cap)
        else:
            (res.missing_mandatory if level == "mandatory" else res.skipped_optional).append(cap)
    return res


def suggest_mcp_config(capabilities: Any, *, prefer_non_auth: bool = True) -> dict[str, Any]:
    """A ready-to-paste ``mcpServers`` block covering ``capabilities``.

    Picks one known server per capability, preferring non-auth so the example
    runs without secrets. Returns ``{"mcpServers": {name: config, ...}}``.
    """
    caps = list(normalize_requirements(capabilities).keys()) or list(capabilities or [])
    servers: dict[str, Any] = {}
    for cap in caps:
        options = servers_for(cap)
        if prefer_non_auth:
            options = sorted(options, key=lambda s: (s.needs_auth, s.name))
        if options:
            s = options[0]
            servers[s.name] = s.to_config()
    return {"mcpServers": servers}
