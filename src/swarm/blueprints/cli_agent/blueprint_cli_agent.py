"""CLI Agent blueprint — expose a single configured agentic CLI over the
OpenAI-compatible API.

This is the minimal drop-in: a request to ``model: "cli_agent"`` runs one
configured CLI (``claude``, ``gemini``, ...) one-shot and streams its answer
back as a normal chat completion. Which CLI runs is chosen by (in order) the
per-request ``cli`` param, the config ``cli_fusion.default_cli``, or the first
CLI actually installed on this host.

See :mod:`swarm.core.cli_adapter` for the lifecycle layer and
``cli_fusion`` for multi-CLI deliberation.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, ClassVar

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.blueprint_base import BlueprintBase

logger = logging.getLogger(__name__)


class CliAgentBlueprint(BlueprintBase):
    """Run one configured agentic CLI as an OpenAI-compatible model."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "cli_agent",
        "title": "CLI Agent (single external CLI)",
        "description": (
            "Expose a single configured agentic CLI (claude, gemini, codex, ...) "
            "over the OpenAI-compatible API. The 'cli' param selects which one."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["cli", "subagent", "adapter", "openai-compatible"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(self, blueprint_id: str = "cli_agent", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        """Capture per-request params forwarded by the API view."""
        self._params = dict(params or {})

    async def run(self, messages: list[dict[str, Any]], **kwargs) -> Any:
        prompt = support.render_prompt(messages)
        if not prompt:
            yield support.message_chunk("No prompt provided.", final=True)
            return

        registry = support.apply_overrides(
            support.build_registry(self._config), self._params
        )
        name = support.select_single_cli(self._config, self._params, registry)
        if not name:
            yield support.message_chunk(
                "No CLI agents are configured. Add a 'cli_agents' block to your "
                "swarm config (see docs/CLI_FUSION.md).",
                final=True,
            )
            return

        try:
            adapter = registry.get(name)
        except Exception as exc:  # CliAdapterError
            yield support.message_chunk(str(exc), final=True)
            return

        workdir = self._params.get(support.PARAM_WORKDIR)
        yield support.progress_chunk(f"_Running CLI agent `{name}`…_")
        result = await adapter.run(prompt, workdir=workdir)

        if not result.ok:
            yield support.message_chunk(
                support.format_cli_error(adapter, result.error or "unknown error"),
                final=True,
            )
            return

        content = result.text
        if result.parse_error:
            logger.warning("CLI %s parse issue: %s", name, result.parse_error)
        yield support.message_chunk(content, final=True)
