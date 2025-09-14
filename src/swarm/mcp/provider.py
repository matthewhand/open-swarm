"""
MCP Provider (skeleton) for exposing Open Swarm blueprints as tools.

This module is framework-agnostic and can be used by a Django MCP server
integration (e.g., `django-mcp-server`) to enumerate tools and execute calls.

Design goals:
- No hard dependency on MCP server package.
- Safe defaults; minimal schema (single `instruction` string parameter).
- Forward-compatible with richer, per-blueprint schemas and streaming.
"""
from __future__ import annotations

from typing import Any, Dict, List

from swarm.core.blueprint_discovery import discover_blueprints
from swarm.settings import BLUEPRINT_DIRECTORY


class BlueprintMCPProvider:
    """Enumerate blueprints as MCP tools and allow simple invocation.

    MVP tool schema:
      - name: blueprint id (directory name)
      - parameters: { type: "object", properties: { instruction: { type: "string" } }, required: ["instruction"] }
      - description: from blueprint metadata or docstring

    Execution MVP:
      - Returns a simple text response acknowledging the tool call.
      - Integrating with real blueprint execution (Runner/BlueprintBase) is a TODO.
    """

    def __init__(self, blueprint_dir: str | None = None) -> None:
        self._blueprint_dir = blueprint_dir or BLUEPRINT_DIRECTORY
        self._index: Dict[str, Dict[str, Any]] = {}
        self.refresh()

    def refresh(self) -> None:
        """Re-discover blueprints and rebuild the internal index."""
        discovered = discover_blueprints(self._blueprint_dir)
        index: Dict[str, Dict[str, Any]] = {}
        for key, info in discovered.items():
            meta = info.get("metadata", {}) if isinstance(info, dict) else {}
            name = meta.get("name", key)
            description = meta.get("description") or f"Blueprint {name}"
            index[key] = {
                "id": key,
                "name": name,
                "description": description,
            }
        self._index = index

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return MCP-style tool definitions for all discovered blueprints."""
        tools: List[Dict[str, Any]] = []
        for key, entry in self._index.items():
            tools.append(
                {
                    "name": key,
                    "description": entry.get("description") or entry.get("name") or key,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "instruction": {"type": "string", "description": "Instruction or message for the blueprint"}
                        },
                        "required": ["instruction"],
                    },
                }
            )
        return tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool (blueprint) with arguments. MVP returns a simple reply.

        TODO: Integrate with actual blueprint execution (Runner/BlueprintBase) and
        capture output. Consider structured outputs when available.
        """
        if name not in self._index:
            raise ValueError(f"Unknown tool: {name}")
        instruction = arguments.get("instruction", "")
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("'instruction' must be a non-empty string")
        # MVP reply
        return {
            "content": f"[Blueprint:{name}] Received instruction: {instruction}",
        }

