"""Integration layer between BlueprintMCPProvider and django-mcp-server.

This remains import-guarded and safe when the MCP server package is absent.
"""
from __future__ import annotations

from typing import Any, Dict, Callable

from .provider import BlueprintMCPProvider


def register_blueprints_with_mcp() -> int:
    """Register discovered blueprints as MCP tools.

    Returns the number of tools registered. If the MCP server module is missing,
    returns 0 without raising.
    """
    try:
        # Expected simple registry API in django-mcp-server
        from django_mcp_server import registry  # type: ignore
    except Exception:
        return 0

    provider = BlueprintMCPProvider()
    count = 0
    for tool in provider.list_tools():
        name = tool.get("name")
        parameters = tool.get("parameters")
        description = tool.get("description")

        def make_handler(n: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
            def _handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
                return provider.call_tool(n, arguments)

            return _handler

        try:
            registry.register_tool(name=name, parameters=parameters, description=description, handler=make_handler(name))
            count += 1
        except Exception:
            # Skip tool on registration error (keeps process robust)
            continue

    return count

