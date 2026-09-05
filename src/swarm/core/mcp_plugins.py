"""Plugins manage path (#502): swarm as an MCP *client*.

Server topology is global (``swarm_config.json`` ``mcpServers``). Tool On/Off
is per-chat (#805 ``params.enabled_tools``). Distinct from
``ENABLE_MCP_SERVER`` (exposing swarm *as* an MCP server).

Local servers use stdio (command + args + env ``${VAR}``). Remote servers use
a URL plus optional headers whose values are env placeholders — never plaintext
secrets. Live ``list_tools`` is injectable so CI uses fixture mocks, not hosts.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections.abc import Callable, Iterable, Mapping
from contextlib import suppress
from typing import Any
from urllib.parse import urlparse

from swarm.core.chat_plugin_tools import PLUGIN_CATALOG_IDS, apply_chat_plugin_allowlist
from swarm.core.cli_mcp import normalize_mcp_servers
from swarm.core.config_ownership import (
    ConfigOwnershipError,
    is_placeholder,
    looks_like_env_name,
    refuse_plaintext_secrets,
)

logger = logging.getLogger(__name__)

KIND_LOCAL = "local"
KIND_REMOTE = "remote"
_PLACEHOLDER_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_SAFE_URL_SCHEMES = frozenset({"http", "https"})

ListToolsFn = Callable[[dict[str, Any]], list[dict[str, str]]]


class McpPluginError(Exception):
    """Honest operator-facing MCP plugin failure (connect / validate)."""

    def __init__(self, message: str, *, code: str = "mcp_plugin_error", status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


def _slug(name: str) -> str:
    raw = (name or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug or "mcp-server"


def _str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        parts = [part.strip() for part in re.split(r"[\s,]+", value) if part.strip()]
        return parts
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _placeholder_map(value: Any, *, field: str) -> dict[str, str]:
    """Keep only ``${VAR}`` / ENV_NAME values. Refuse plaintext secrets."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise McpPluginError(f"{field} must be an object of ${{VAR}} placeholders.", code="bad_payload")
    out: dict[str, str] = {}
    for raw_key, raw_val in value.items():
        key = str(raw_key).strip()
        if not key:
            continue
        if raw_val is None or raw_val == "":
            continue
        if not isinstance(raw_val, str):
            raise McpPluginError(
                f"Refusing plaintext secret at {field}.{key}. Use ${{ENV_VAR}}.",
                code="plaintext_secret",
            )
        trimmed = raw_val.strip()
        if is_placeholder(trimmed):
            out[key] = trimmed
            continue
        if looks_like_env_name(trimmed):
            out[key] = f"${{{trimmed}}}"
            continue
        raise McpPluginError(
            f"Refusing plaintext secret at {field}.{key}. Use ${{ENV_VAR}}.",
            code="plaintext_secret",
        )
    return out


def _kind_of(spec: Mapping[str, Any] | None) -> str:
    raw = spec or {}
    explicit = str(raw.get("kind") or raw.get("type") or raw.get("transport") or "").strip().lower()
    if explicit in {KIND_LOCAL, "stdio"}:
        return KIND_LOCAL
    if explicit in {KIND_REMOTE, "http", "sse", "url"}:
        return KIND_REMOTE
    if isinstance(raw.get("url"), str) and raw["url"].strip():
        return KIND_REMOTE
    return KIND_LOCAL


def _validate_remote_url(url: str) -> str:
    trimmed = (url or "").strip()
    if not trimmed:
        raise McpPluginError("Remote MCP servers need an http(s) URL.", code="bad_payload")
    parsed = urlparse(trimmed)
    if parsed.scheme not in _SAFE_URL_SCHEMES or not parsed.netloc:
        raise McpPluginError(
            "Remote MCP URL must be http(s) with a host. Do not paste secrets in the URL.",
            code="bad_payload",
        )
    if parsed.username or parsed.password:
        raise McpPluginError(
            "Refusing credentials in the remote MCP URL. Use a ${VAR} header instead.",
            code="plaintext_secret",
        )
    return trimmed


def normalize_plugin_spec(raw: Any, *, name: str = "") -> dict[str, Any]:
    """Normalize a Plugins UI / API body into a ``mcpServers`` entry."""
    if not isinstance(raw, dict):
        raise McpPluginError("Server config must be an object.", code="bad_payload")
    try:
        refuse_plaintext_secrets(raw)
    except ConfigOwnershipError as exc:
        raise McpPluginError(str(exc), code=exc.code, status=exc.status) from exc
    display = str(raw.get("label") or raw.get("name") or name).strip()
    key = _slug(str(raw.get("id") or raw.get("name") or name))
    kind = _kind_of(raw)
    enabled = raw.get("enabled")
    entry: dict[str, Any] = {
        "name": key,
        "label": display or key,
        "kind": kind,
        "enabled": not (enabled is False or enabled == "false"),
        "provides": _str_list(raw.get("provides")),
        "note": str(raw.get("note") or "").strip(),
    }
    env = _placeholder_map(raw.get("env"), field="env")
    if env:
        entry["env"] = env
    headers = _placeholder_map(raw.get("headers"), field="headers")
    if headers:
        entry["headers"] = headers
    discovered = raw.get("discovered_tools") or raw.get("tools")
    if isinstance(discovered, list):
        tools: list[dict[str, str]] = []
        for item in discovered:
            if not isinstance(item, dict):
                continue
            tool_name = str(item.get("name") or "").strip()
            if not tool_name:
                continue
            tools.append(
                {
                    "name": tool_name,
                    "description": str(item.get("description") or "").strip(),
                }
            )
        if tools:
            entry["discovered_tools"] = tools
            if not entry["provides"]:
                entry["provides"] = [row["name"] for row in tools]
    if kind == KIND_REMOTE:
        entry["url"] = _validate_remote_url(str(raw.get("url") or ""))
        transport = str(raw.get("type") or raw.get("transport") or "sse").strip() or "sse"
        entry["type"] = transport
    else:
        command = str(raw.get("command") or "").strip()
        if not command:
            raise McpPluginError("Local MCP servers need a command (stdio).", code="bad_payload")
        entry["command"] = command
        entry["args"] = _str_list(raw.get("args"))
        cwd = str(raw.get("cwd") or "").strip()
        if cwd:
            entry["cwd"] = cwd
    return entry


def spec_to_config_entry(spec: Mapping[str, Any]) -> dict[str, Any]:
    """``swarm_config.json`` ``mcpServers`` value (no duplicate name key)."""
    entry = dict(spec)
    entry.pop("name", None)
    return entry


def public_server(name: str, spec: Mapping[str, Any] | None) -> dict[str, Any]:
    """Redacted server row for the Plugins UI. No secret values."""
    from swarm.core.config_ownership import redact_for_api

    raw = spec if isinstance(spec, dict) else {}
    kind = _kind_of(raw)
    redacted = redact_for_api(raw)
    tools = []
    discovered = raw.get("discovered_tools")
    if isinstance(discovered, list):
        tools = [
            {
                "name": str(item.get("name") or "").strip(),
                "description": str(item.get("description") or "").strip(),
            }
            for item in discovered
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
    if not tools:
        tools = [
            {"name": cap, "description": str(raw.get("note") or "").strip()}
            for cap in _str_list(raw.get("provides"))
        ]
    return {
        "name": name,
        "label": str(raw.get("label") or name),
        "kind": kind,
        "enabled": raw.get("enabled") is not False,
        "command": str(redacted.get("command") or ""),
        "args": list(redacted.get("args") or []),
        "url": str(redacted.get("url") or ""),
        "type": str(redacted.get("type") or redacted.get("transport") or ""),
        "cwd": str(redacted.get("cwd") or ""),
        "env": redacted.get("env") if isinstance(redacted.get("env"), dict) else {},
        "headers": redacted.get("headers") if isinstance(redacted.get("headers"), dict) else {},
        "provides": _str_list(raw.get("provides")),
        "note": str(raw.get("note") or ""),
        "tools": tools,
    }


def load_mcp_servers(config: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    raw = (config or {}).get("mcpServers")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for name, spec in raw.items():
        key = str(name).strip()
        if not key or not isinstance(spec, dict):
            continue
        out[key] = dict(spec)
    return out


def enabled_mcp_servers(config: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Enabled local/remote servers (``enabled: false`` dropped)."""
    return normalize_mcp_servers(load_mcp_servers(config))


def plugin_catalog_ids(config: Mapping[str, Any] | None = None) -> frozenset[str]:
    """Fixture ids plus discovered / provides names from configured servers."""
    ids = set(PLUGIN_CATALOG_IDS)
    for spec in load_mcp_servers(config).values():
        if spec.get("enabled") is False:
            continue
        for item in spec.get("discovered_tools") or []:
            if isinstance(item, dict) and item.get("name"):
                ids.add(str(item["name"]).strip())
        for cap in _str_list(spec.get("provides")):
            ids.add(cap)
    return frozenset(name for name in ids if name)


def _expand_placeholders(value: Any) -> Any:
    from swarm.core.config_loader import _substitute_env_vars

    return _substitute_env_vars(value)


def _missing_env(spec: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in ("env", "headers"):
        block = spec.get(field)
        if not isinstance(block, dict):
            continue
        for _key, raw in block.items():
            name = ""
            if isinstance(raw, str):
                match = _PLACEHOLDER_RE.match(raw.strip())
                name = match.group(1) if match else (raw.strip() if looks_like_env_name(raw) else "")
            if name and not os.environ.get(name, "").strip():
                missing.append(name)
    return missing


def _tool_rows(tools: Iterable[Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for tool in tools:
        if isinstance(tool, dict):
            name = str(tool.get("name") or "").strip()
            description = str(tool.get("description") or "").strip()
        else:
            name = str(getattr(tool, "name", "") or "").strip()
            description = str(getattr(tool, "description", "") or "").strip()
        if name:
            rows.append({"name": name, "description": description})
    return rows


async def _discover_local(spec: Mapping[str, Any], *, timeout: int) -> list[dict[str, str]]:
    from swarm.extensions.mcp.mcp_client import MCPClient

    client = MCPClient(
        {
            "command": spec.get("command"),
            "args": list(spec.get("args") or []),
            "env": spec.get("env") or {},
        },
        timeout=timeout,
        debug=False,
    )
    return _tool_rows(await client.list_tools())


async def _discover_remote(spec: Mapping[str, Any], *, timeout: int) -> list[dict[str, str]]:
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    url = str(spec.get("url") or "")
    headers = spec.get("headers") if isinstance(spec.get("headers"), dict) else None
    # Never log header values — they may contain resolved secrets after expand.
    async with (
        sse_client(url, headers=headers, timeout=float(timeout)) as (read, write),
        ClientSession(read, write) as session,
    ):
        await asyncio.wait_for(session.initialize(), timeout=timeout)
        response = await asyncio.wait_for(session.list_tools(), timeout=timeout)
        return _tool_rows(getattr(response, "tools", None) or [])


async def _discover_live(spec: Mapping[str, Any], *, timeout: int = 15) -> list[dict[str, str]]:
    kind = _kind_of(spec)
    if kind == KIND_REMOTE:
        return await _discover_remote(spec, timeout=timeout)
    return await _discover_local(spec, timeout=timeout)


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise McpPluginError(
        "MCP discover was called from a running event loop without a mock.",
        code="mcp_discover_failed",
        status=500,
    )


def list_tools_for_spec(
    spec: Mapping[str, Any],
    *,
    list_tools_fn: ListToolsFn | None = None,
    timeout: int = 15,
) -> list[dict[str, str]]:
    """Connect and list tools. ``list_tools_fn`` is the CI/test seam (no live host)."""
    normalized = normalize_plugin_spec(dict(spec), name=str(spec.get("name") or "server"))
    if normalized.get("enabled") is False:
        raise McpPluginError("Server is disabled. Enable it before discovering tools.", code="disabled")
    if list_tools_fn is not None:
        return _tool_rows(list_tools_fn(normalized))
    missing = _missing_env(normalized)
    if missing:
        names = ", ".join(sorted(set(missing)))
        raise McpPluginError(
            f"Secret env {names} is not set. Export the variable; do not paste the value.",
            code="secret_unset",
        )
    live = _expand_placeholders(normalized)
    try:
        return _tool_rows(_run_async(_discover_live(live, timeout=timeout)))
    except McpPluginError:
        raise
    except Exception as exc:
        logger.warning("MCP list_tools failed for %s", normalized.get("name") or normalized.get("kind"))
        raise McpPluginError(
            f"Could not list tools from the MCP server: {exc}",
            code="mcp_discover_failed",
            status=502,
        ) from exc


def discover_and_store(
    name: str,
    spec: Mapping[str, Any] | None = None,
    *,
    config: Mapping[str, Any] | None = None,
    list_tools_fn: ListToolsFn | None = None,
    persist: bool = True,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Discover tools for a named server (saved or draft). Optionally persist names."""
    key = _slug(name)
    saved = load_mcp_servers(config).get(key)
    raw = dict(saved or {})
    if spec:
        raw.update(spec)
    raw.setdefault("name", key)
    normalized = normalize_plugin_spec(raw, name=key)
    tools = list_tools_for_spec(normalized, list_tools_fn=list_tools_fn)
    normalized["discovered_tools"] = tools
    normalized["provides"] = [row["name"] for row in tools]
    if persist and saved is not None:
        from swarm.core.config_ownership import persist_webui_section

        persist_webui_section(
            "mcpServers",
            upsert={key: spec_to_config_entry(normalized)},
        )
    return tools, normalized


def _iter_agents(blueprint: Any) -> list[Any]:
    agents: list[Any] = []
    raw = getattr(blueprint, "agents", None)
    if isinstance(raw, dict):
        agents.extend(raw.values())
    elif isinstance(raw, list):
        agents.extend(raw)
    starting = getattr(blueprint, "starting_agent", None)
    if starting is not None and not callable(starting) and starting not in agents:
        agents.append(starting)
    return agents


def _make_tool_caller(tool_name: str, spec: Mapping[str, Any]) -> Callable[..., Any]:
    body = dict(spec)

    async def _call(**kwargs: Any) -> Any:
        live = _expand_placeholders(body)
        if _kind_of(live) == KIND_REMOTE:
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            headers = live.get("headers") if isinstance(live.get("headers"), dict) else None
            async with (
                sse_client(str(live.get("url") or ""), headers=headers, timeout=15.0) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                return await session.call_tool(tool_name, kwargs)
        from swarm.extensions.mcp.mcp_client import MCPClient

        client = MCPClient(
            {
                "command": live.get("command"),
                "args": list(live.get("args") or []),
                "env": live.get("env") or {},
            },
            timeout=15,
        )
        fn = client._create_tool_callable(tool_name)
        return await fn(**kwargs)

    return _call


def _tools_from_server(name: str, spec: Mapping[str, Any]) -> list[Any]:
    from swarm.types import Tool

    metas = spec.get("discovered_tools")
    if not isinstance(metas, list) or not metas:
        metas = [{"name": cap, "description": str(spec.get("note") or "")} for cap in _str_list(spec.get("provides"))]
    tools: list[Any] = []
    for item in metas:
        if isinstance(item, dict):
            tool_name = str(item.get("name") or "").strip()
            description = str(item.get("description") or "").strip()
        else:
            tool_name = str(item).strip()
            description = ""
        if not tool_name:
            continue
        tools.append(
            Tool(
                name=tool_name,
                description=description or f"{name} MCP tool",
                func=_make_tool_caller(tool_name, spec),
                dynamic=True,
            )
        )
    return tools


def attach_plugin_mcp_tools(blueprint: Any, config: Mapping[str, Any] | None) -> list[str]:
    """Attach tools from enabled MCP servers. Disabled / missing servers add nothing."""
    attached: list[str] = []
    servers = enabled_mcp_servers(config)
    extras = {name: load_mcp_servers(config).get(name, {}) for name in servers}
    for name, spec in servers.items():
        merged = {**extras.get(name, {}), **spec}
        tools = _tools_from_server(name, merged)
        if not tools:
            continue
        for agent in _iter_agents(blueprint):
            names = getattr(agent, "mcp_servers", None)
            if isinstance(names, list) and name not in names:
                names.append(name)
            elif names is None:
                with suppress(Exception):
                    agent.mcp_servers = [name]
            for attr in ("functions", "tools"):
                current = getattr(agent, attr, None)
                if not isinstance(current, list):
                    continue
                have = {getattr(fn, "name", None) or getattr(fn, "__name__", None) for fn in current}
                for tool in tools:
                    if tool.name not in have:
                        current.append(tool)
                        have.add(tool.name)
                        attached.append(tool.name)
    return attached


def apply_plugin_mcp_runtime(
    blueprint: Any,
    config: Mapping[str, Any] | None,
    enabled_tools: Iterable[Any] | None,
) -> None:
    """Attach enabled-server tools, then apply the per-chat allowlist (#805)."""
    attach_plugin_mcp_tools(blueprint, config)
    apply_chat_plugin_allowlist(
        blueprint,
        enabled_tools,
        catalog_ids=plugin_catalog_ids(config),
    )


def swarm_config() -> dict[str, Any]:
    try:
        from django.apps import apps

        cfg = getattr(apps.get_app_config("swarm"), "config", None)
        if isinstance(cfg, dict):
            return cfg
    except Exception:
        logger.debug("swarm AppConfig.config unavailable", exc_info=True)
    try:
        from swarm.core.server_config import load_server_config

        loaded = load_server_config()
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}
