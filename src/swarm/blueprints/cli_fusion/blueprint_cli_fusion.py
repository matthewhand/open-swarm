"""Legacy model id ``cli_fusion`` → read-only Mixture of Agents.

Historical multi-writer fusion is retired. This module re-exports
:class:`~swarm.blueprints.moa.blueprint_moa.MoABlueprint` so
``model: "cli_fusion"`` keeps resolving without a separate multi-writer panel.
"""

from __future__ import annotations

from typing import Any, ClassVar

from swarm.blueprints.moa.blueprint_moa import MoABlueprint


class CliFusionBlueprint(MoABlueprint):
    """Back-compat alias for MoA (read-only consensus participants)."""

    metadata: ClassVar[dict[str, Any]] = {
        **dict(MoABlueprint.metadata),
        "name": "cli_fusion",
        "title": "CLI Fusion (legacy → MoA read-only)",
        "description": (
            "Legacy alias for Mixture of Agents. Participants are read-only; "
            "orchestrator determines and alone may write. Prefer model id 'moa'."
        ),
        "tags": ["moa", "legacy", "cli_fusion", "readonly"],
    }


# Discovery picks CliFusionBlueprint; MoA is the implementation.
__all__ = ["CliFusionBlueprint", "MoABlueprint"]
