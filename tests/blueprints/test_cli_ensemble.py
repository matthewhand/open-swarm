"""cli_ensemble is the canonical name for cli_fusion (multi-CLI deliberation).

It must subclass the fusion implementation, be discovered under its own key, and
run over the shared ``cli_fusion`` config block exactly like cli_fusion.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from swarm.blueprints.cli_ensemble.blueprint_cli_ensemble import CliEnsembleBlueprint
from swarm.blueprints.moa.blueprint_moa import MoABlueprint
from swarm.core.blueprint_discovery import discover_blueprints

PY = sys.executable

def test_is_subclass_of_fusion():
    assert issubclass(CliEnsembleBlueprint, MoABlueprint)
    assert CliEnsembleBlueprint.metadata["name"] == "cli_ensemble"


def test_discovered_as_cli_ensemble():
    found = discover_blueprints(str(Path("src/swarm/blueprints").resolve()))
    assert "cli_ensemble" in found
    assert "cli_fusion" in found  # alias still discovered
    # Discovery re-execs the module, so compare by qualified name, not identity.
    assert found["cli_ensemble"]["class_type"].__name__ == "CliEnsembleBlueprint"
