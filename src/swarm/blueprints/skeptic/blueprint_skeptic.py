"""Skeptic — role=skeptic marker (retry-check stub).

Receives the original prompt, checks whether the work was accomplished via
``submit_skeptic_verdict``, and if not would send findings back to the
original agent to retry. The full retry loop is a later PR — this blueprint
only registers the role.
"""

from __future__ import annotations

from typing import Any, ClassVar

from swarm.blueprints.common import cli_fusion_support as fusion
from swarm.core.blueprint_base import BlueprintBase

STUB_REPLY = (
    "Skeptic — call submit_skeptic_verdict (pass/fail). If fail, findings go back to retry."
)


class SkepticBlueprint(BlueprintBase):
    """Discoverable `role=skeptic` marker. No retry engine."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "skeptic",
        "title": "Skeptic",
        "description": "Prompt done? submit_skeptic_verdict pass/fail. If fail, retry.",
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["skeptic", "retry", "stub"],
        "role": "skeptic",
        "required_mcp_servers": [],
        "env_vars": [],
    }

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        yield fusion.message_chunk(STUB_REPLY, final=True)
