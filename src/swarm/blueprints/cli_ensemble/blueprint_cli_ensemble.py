"""CLI Ensemble — the canonical name for multi-CLI deliberation.

Fan a prompt to a panel of configured agentic CLIs in parallel, then a judge
synthesizes one answer (a Mixture-of-Agents / ensemble over your installed CLIs).

This is the **promoted public name** for the pattern. The implementation lives in
:class:`~swarm.blueprints.cli_fusion.blueprint_cli_fusion.CliFusionBlueprint` —
``cli_fusion`` remains the internal primitive (the shared ``cli_fusion`` config
block and ``cli_fusion_support`` helpers are used family-wide) and still resolves
as a back-compat model alias. ``cli_ensemble`` reads the same ``cli_fusion``
config block, so no extra configuration is needed to switch names.

Why not just call it "fusion": OpenRouter Fusion is a hosted *tool a model
invokes*; ours is the *endpoint itself* (panel → judge as the surface you call).
"Ensemble" is the neutral ML term for combining several models into one output.
"""

from __future__ import annotations

from typing import Any, ClassVar

from swarm.blueprints.cli_fusion.blueprint_cli_fusion import CliFusionBlueprint


class CliEnsembleBlueprint(CliFusionBlueprint):
    """Multi-CLI deliberation (panel → judge → synthesize). Canonical name."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "cli_ensemble",
        "title": "CLI Ensemble (multi-CLI deliberation)",
        "description": (
            "Fan a prompt to a panel of configured agentic CLIs in parallel, "
            "judge and synthesize their answers into one. A Mixture-of-Agents "
            "ensemble over your installed CLIs. (Formerly cli_fusion, which "
            "still works as an alias.)"
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["cli", "ensemble", "consensus", "multi-agent", "deliberation", "openai-compatible"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(self, blueprint_id: str = "cli_ensemble", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
