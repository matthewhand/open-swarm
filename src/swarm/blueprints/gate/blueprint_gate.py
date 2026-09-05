"""Gate — role=gate marker (approval classifier stub).

Classifies a tool call as dangerous or not by calling ``submit_gate_verdict``.
Until a gate is wired, every tool call is approved. The full
ask-user-on-dangerous loop is a later PR — this blueprint only registers the
role so the AGENTS sidepane can style it, and so Support can point at it.
"""

from __future__ import annotations

from typing import Any, ClassVar

from swarm.blueprints.common import cli_fusion_support as fusion
from swarm.core.blueprint_base import BlueprintBase

STUB_REPLY = (
    "Gate — call submit_gate_verdict (yes=dangerous / no=safe). Until wired, all approved."
)


class GateBlueprint(BlueprintBase):
    """Discoverable `role=gate` marker. No approval engine."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "gate",
        "title": "Gate",
        "description": "Dangerous? submit_gate_verdict yes/no. Until wired, all approved.",
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["gate", "approval", "stub"],
        "role": "gate",
        "rail": True,
        "required_mcp_servers": [],
        "env_vars": [],
    }

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        yield fusion.message_chunk(STUB_REPLY, final=True)
