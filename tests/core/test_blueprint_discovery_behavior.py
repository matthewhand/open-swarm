"""
Stronger smoke tests for blueprint discovery.

- Validates discovery against the real repo blueprints (non-invasive)
- Validates metadata/docstring fallback behavior using a temporary blueprint
"""
from __future__ import annotations

from pathlib import Path

import inspect
import textwrap

import pytest

from swarm.core.blueprint_discovery import discover_blueprints
from swarm.core.blueprint_base import BlueprintBase


def test_discover_repo_blueprints_includes_codey():
    """
    Discover blueprints from the repo and ensure at least one known blueprint
    (codey) is detected with a valid BlueprintBase subclass and metadata shape.
    """
    repo_blueprints = discover_blueprints("src/swarm/blueprints")

    # Ensure we detect codey (present in the repo) without coupling to its internals.
    assert "codey" in repo_blueprints, "Expected 'codey' blueprint to be discoverable"

    info = repo_blueprints["codey"]
    cls = info["class_type"]
    meta = info["metadata"]

    # Class should be a subclass of BlueprintBase
    assert inspect.isclass(cls)
    assert issubclass(cls, BlueprintBase)

    # Metadata should contain at least a name; description may be provided via
    # metadata or docstring depending on the blueprint implementation.
    assert isinstance(meta.get("name"), str) and meta["name"].strip() != ""
    # Optional fields are allowed to be None, but keys should exist consistently
    assert "version" in meta and "description" in meta and "author" in meta and "abbreviation" in meta


def test_discover_blueprints_docstring_fallback_and_name_default(tmp_path: Path):
    """
    Create a temporary blueprint with no description in metadata to validate that
    discovery uses the class docstring for description, and falls back to the
    directory name for the metadata 'name' when not provided.
    """
    # Layout: <tmp>/blueprints/my_temp_bp/blueprint_my_temp_bp.py
    bp_root = tmp_path / "blueprints"
    bp_dir = bp_root / "my_temp_bp"
    bp_dir.mkdir(parents=True)

    code = textwrap.dedent(
        '''
        from swarm.core.blueprint_base import BlueprintBase

        class MyTempBlueprint(BlueprintBase):
            """Docstring description should be used when metadata lacks it."""
            metadata = {
                # deliberately omit 'name' and 'description' to exercise defaults
                'version': '0.1.0',
                'author': 'Temp Tester',
                'abbreviation': 'tmp'
            }
        '''
    )
    (bp_dir / "blueprint_my_temp_bp.py").write_text(code)

    discovered = discover_blueprints(str(bp_root))
    assert "my_temp_bp" in discovered, "Expected temporary blueprint to be discovered"

    info = discovered["my_temp_bp"]
    meta = info["metadata"]

    # Name should fall back to directory name when not provided in metadata
    assert meta.get("name") == "my_temp_bp"
    # Description should come from the class docstring
    assert meta.get("description") == "Docstring description should be used when metadata lacks it."
