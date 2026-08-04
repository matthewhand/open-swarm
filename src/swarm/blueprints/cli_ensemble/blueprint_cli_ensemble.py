"""Legacy model id ``cli_ensemble`` → read-only Mixture of Agents."""

from __future__ import annotations

from typing import Any, ClassVar

from swarm.blueprints.moa.blueprint_moa import MoABlueprint


class CliEnsembleBlueprint(MoABlueprint):
    """Back-compat alias for MoA (read-only consensus participants)."""

    metadata: ClassVar[dict[str, Any]] = {
        **dict(MoABlueprint.metadata),
        "name": "cli_ensemble",
        "title": "CLI Ensemble (legacy → MoA read-only)",
        "description": (
            "Legacy alias for Mixture of Agents. Prefer model id 'moa'."
        ),
        "tags": ["moa", "legacy", "cli_ensemble", "readonly"],
    }


__all__ = ["CliEnsembleBlueprint", "MoABlueprint"]
