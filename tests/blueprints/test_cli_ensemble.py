"""cli_ensemble is the canonical name for cli_fusion (multi-CLI deliberation).

It must subclass the fusion implementation, be discovered under its own key, and
run over the shared ``cli_fusion`` config block exactly like cli_fusion.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from swarm.blueprints.cli_ensemble.blueprint_cli_ensemble import CliEnsembleBlueprint
from swarm.blueprints.cli_fusion.blueprint_cli_fusion import CliFusionBlueprint
from swarm.core.blueprint_discovery import discover_blueprints

PY = sys.executable


def _echo(prefix: str) -> dict:
    return {"cmd": [PY, "-c", f"import sys; print('{prefix}:' + sys.argv[1])", "{prompt}"]}


def _judge_emitting(obj: dict) -> dict:
    payload = json.dumps(obj).replace("'", "\\'")
    return {"cmd": [PY, "-c", f"import sys; print('{payload}')", "{prompt}"]}


def _config() -> dict:
    return {
        "cli_agents": {"a": _echo("A"), "b": _echo("B"), "judge": _judge_emitting({"answer": "SYNTHESIZED", "done": True})},
        "cli_fusion": {"presets": {"p": {"panel": ["a", "b"], "judge": "judge"}}, "default_preset": "p", "max_rounds": 1},
    }


def test_is_subclass_of_fusion():
    assert issubclass(CliEnsembleBlueprint, CliFusionBlueprint)
    assert CliEnsembleBlueprint.metadata["name"] == "cli_ensemble"


def test_discovered_as_cli_ensemble():
    found = discover_blueprints(str(Path("src/swarm/blueprints").resolve()))
    assert "cli_ensemble" in found
    assert "cli_fusion" in found  # alias still discovered
    # Discovery re-execs the module, so compare by qualified name, not identity.
    assert found["cli_ensemble"]["class_type"].__name__ == "CliEnsembleBlueprint"


async def test_runs_over_shared_fusion_config():
    bp = CliEnsembleBlueprint(config=_config())
    bp.set_params({})
    chunks = [c async for c in bp.run([{"role": "user", "content": "q"}])]
    final = None
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content") is not None:
            final = msgs[0]["content"]
    assert final == "SYNTHESIZED"  # judge synthesized, identical to cli_fusion
