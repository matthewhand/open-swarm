"""External/community blueprint discovery (discover_all_blueprints).

Community blueprints live outside the bundled tree and are loaded under a
synthetic namespace so they cannot shadow or collide with swarm.blueprints.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from swarm.core.blueprint_discovery import (
    discover_all_blueprints,
    discover_blueprints,
)

# A minimal, self-contained community blueprint that subclasses the real base.
_COMMUNITY_BP = textwrap.dedent(
    '''
    from collections.abc import AsyncGenerator
    from typing import Any

    from swarm.core.blueprint_base import BlueprintBase


    class AcmeBlueprint(BlueprintBase):
        metadata = {"name": "acme", "description": "community demo"}

        async def run(self, messages, **kwargs) -> "AsyncGenerator[dict[str, Any], None]":
            yield {"messages": [{"role": "assistant", "content": "acme"}]}
    '''
)


def _write_community_pack(root: Path, name: str = "acme") -> Path:
    bp_dir = root / name
    bp_dir.mkdir(parents=True)
    (bp_dir / f"blueprint_{name}.py").write_text(_COMMUNITY_BP)
    return root


def test_external_root_is_discovered_under_namespace(tmp_path):
    community = _write_community_pack(tmp_path / "community")
    found = discover_blueprints(str(community), namespace="swarm_community_test")
    assert "acme" in found
    cls = found["acme"]["class_type"]
    # Loaded under the synthetic namespace, NOT swarm.blueprints.*
    assert cls.__module__.startswith("swarm_community_test.")


def test_discover_all_merges_bundled_and_community(tmp_path):
    community = _write_community_pack(tmp_path / "community")
    bundled = Path("src/swarm/blueprints").resolve()
    merged = discover_all_blueprints(str(bundled), [str(community)])
    # A known bundled blueprint and the community one both present.
    assert "cli_fusion" in merged
    assert "acme" in merged


def test_missing_extra_dirs_are_skipped(tmp_path):
    bundled = Path("src/swarm/blueprints").resolve()
    merged = discover_all_blueprints(str(bundled), [str(tmp_path / "does-not-exist")])
    assert "cli_fusion" in merged  # bundled still works; missing root ignored


def test_community_cannot_shadow_bundled(tmp_path):
    # A community pack whose key collides with a bundled blueprint is ignored.
    community = _write_community_pack(tmp_path / "community", name="cli_fusion")
    bundled = Path("src/swarm/blueprints").resolve()
    merged = discover_all_blueprints(str(bundled), [str(community)])
    # The bundled cli_fusion wins — its description is not the community stub.
    assert merged["cli_fusion"]["metadata"].get("description") != "community demo"
