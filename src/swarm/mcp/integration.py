"""Integration layer between BlueprintMCPProvider and django-mcp-server.

This remains import-guarded and safe when the MCP server package is absent.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .provider import BlueprintMCPProvider


def register_blueprints_with_mcp() -> int:
    """Register discovered blueprints as MCP tools.

    Returns the number of tools registered. If the MCP server module is missing,
    returns 0 without raising.

    NOTE (2026-06-19): `django-mcp-server` (module `mcp_server`) ≥0.5 exposes an
    ``MCPToolset`` / decorator API, NOT the flat ``registry.register_tool(...)``
    this was written against — so this bridge is a **no-op** today and needs
    porting to the toolset paradigm (tracked in ROADMAP §3.3). The mount itself
    (``/mcp/`` via ``mcp_server.urls``) does work once the ``[mcp]`` extra is
    installed; only the blueprint→tool bridge below is unported.
    """
    try:
        # Legacy/expected flat registry API — absent in mcp_server >=0.5 (see note).
        from mcp_server import registry  # type: ignore
    except Exception:
        return 0

    provider = BlueprintMCPProvider()
    count = 0
    for tool in provider.list_tools():
        name = tool.get("name")
        parameters = tool.get("parameters")
        description = tool.get("description")

        def make_handler(n: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
            def _handler(arguments: dict[str, Any]) -> dict[str, Any]:
                return provider.call_tool(n, arguments)

            return _handler

        try:
            registry.register_tool(name=name, parameters=parameters, description=description, handler=make_handler(name))
            count += 1
        except Exception:
            # Skip tool on registration error (keeps process robust)
            continue

    return count

