"""cli_ensemble is a legacy alias name for MoA (via CliFusionBlueprint/MoABlueprint).

Directory ``cli_ensemble`` is discovered separately; implementation is MoA-class.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.blueprints.cli_ensemble.blueprint_cli_ensemble import CliEnsembleBlueprint
from swarm.blueprints.cli_fusion.blueprint_cli_fusion import CliFusionBlueprint
from swarm.blueprints.moa.blueprint_moa import MoABlueprint
from swarm.core.blueprint_discovery import discover_blueprints


def test_is_subclass_of_fusion_and_moa():
    assert issubclass(CliEnsembleBlueprint, CliFusionBlueprint) or issubclass(
        CliEnsembleBlueprint, MoABlueprint
    )
    assert issubclass(CliEnsembleBlueprint, MoABlueprint)
    assert CliEnsembleBlueprint.metadata["name"] == "cli_ensemble"


def test_discovered_as_cli_ensemble():
    found = discover_blueprints(str(Path("src/swarm/blueprints").resolve()))
    assert "cli_ensemble" in found
    assert "cli_fusion" in found
    for key in ("cli_ensemble", "cli_fusion"):
        mro = [c.__name__ for c in found[key]["class_type"].__mro__]
        assert "MoABlueprint" in mro or "CliFusionBlueprint" in mro or "CliEnsembleBlueprint" in mro


@pytest.mark.asyncio
async def test_runs_moa_fake_responses():
    bp = CliEnsembleBlueprint(config={})
    bp.set_params(
        {
            "participants": ["a", "b"],
            "fake_responses": {
                "a": '{"claim":"SYNTHESIZED","confidence":0.95}',
                "b": '{"claim":"other","confidence":0.4}',
            },
        }
    )
    chunks = [c async for c in bp.run([{"role": "user", "content": "q"}])]
    final = None
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content") is not None:
            final = msgs[0]["content"]
    assert final
    assert "SYNTHESIZED" in final or len(final) > 5
    assert chunks[-1].get("meta", {}).get("moa") is True
