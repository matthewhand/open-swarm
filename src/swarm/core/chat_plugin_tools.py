"""Per-chat plugin tool allowlist (#805).

The SPA sends ``params.enabled_tools`` — ids the operator turned On for the
current chat. Catalog / fixture plugin tools that are Off are excluded.
Blueprint-native functions that are not in the catalog stay available.

v1 catalog ids match the shipped frontend fixture until live MCP list_tools
is wired (#502).
"""

from __future__ import annotations

from typing import Any, Iterable

# Keep in sync with webui/frontend/src/lib/chatPluginTools.ts FIXTURE_PLUGIN_TOOLS.
PLUGIN_CATALOG_IDS: frozenset[str] = frozenset(
    {
        "web_search",
        "web_fetch",
        "browser_navigate",
        "browser_snapshot",
        "browser_click",
        "browser_type",
        "read_file",
        "write_file",
        "list_directory",
        "git_status",
        "git_diff",
        "git_log",
        "get_current_time",
        "convert_timezone",
    }
)


def tool_name(fn: Any) -> str:
    name = getattr(fn, "name", None) or getattr(fn, "__name__", None) or ""
    return str(name)


def filter_plugin_tools_for_chat(
    functions: Iterable[Any] | None,
    enabled_tools: Iterable[Any] | None,
) -> list[Any]:
    """Drop catalog plugin tools that are not in the per-chat allowlist."""
    items = list(functions or [])
    enabled = {str(item).strip() for item in (enabled_tools or []) if str(item).strip()}
    kept: list[Any] = []
    for fn in items:
        name = tool_name(fn)
        if name in PLUGIN_CATALOG_IDS and name not in enabled:
            continue
        kept.append(fn)
    return kept


def _filter_agent(agent: Any, enabled_tools: Iterable[Any] | None) -> None:
    for attr in ("functions", "tools"):
        current = getattr(agent, attr, None)
        if isinstance(current, list):
            setattr(agent, attr, filter_plugin_tools_for_chat(current, enabled_tools))


def apply_chat_plugin_allowlist(blueprint: Any, enabled_tools: Iterable[Any] | None) -> None:
    """Filter plugin tools on a loaded blueprint's agents (in place)."""
    agents = getattr(blueprint, "agents", None)
    if isinstance(agents, dict):
        for agent in agents.values():
            _filter_agent(agent, enabled_tools)
    elif isinstance(agents, list):
        for agent in agents:
            _filter_agent(agent, enabled_tools)
    starting = getattr(blueprint, "starting_agent", None)
    if starting is not None and not callable(starting):
        _filter_agent(starting, enabled_tools)
