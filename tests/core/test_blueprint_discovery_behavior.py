"""
Stronger smoke tests for blueprint discovery.

- Validates discovery against the real repo blueprints (non-invasive)
- Validates metadata/docstring fallback behavior using a temporary blueprint
"""
from __future__ import annotations

import inspect
import textwrap
from pathlib import Path

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.blueprint_discovery import discover_blueprints


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


def test_display_metadata_name_is_not_registered_as_model_id(tmp_path: Path):
    """Display/class metadata names must not pollute discovery keys /v1/models ids."""
    bp_root = tmp_path / "blueprints"
    fancy = bp_root / "fancy_team"
    fancy.mkdir(parents=True)
    (fancy / "blueprint_fancy_team.py").write_text(
        textwrap.dedent(
            '''
            from swarm.core.blueprint_base import BlueprintBase

            class FancyTeamBlueprint(BlueprintBase):
                metadata = {
                    "name": "Fancy Team's Blueprint",
                    "description": "Display name must stay metadata-only.",
                    "version": "0.1.0",
                }
            '''
        )
    )
    slug_alias = bp_root / "slug_team"
    slug_alias.mkdir(parents=True)
    (slug_alias / "blueprint_slug_team.py").write_text(
        textwrap.dedent(
            '''
            from swarm.core.blueprint_base import BlueprintBase

            class SlugTeamBlueprint(BlueprintBase):
                metadata = {
                    "name": "slug-team",
                    "description": "Programmatic slug may be a model id alias.",
                    "version": "0.1.0",
                }
            '''
        )
    )

    discovered = discover_blueprints(str(bp_root))
    assert "fancy_team" in discovered
    assert "Fancy Team's Blueprint" not in discovered
    assert "slug_team" in discovered
    assert "slug-team" in discovered


def test_repo_discovery_skips_display_and_class_metadata_names():
    """Live blueprints keep display/class labels out of model-id keys."""
    discovered = discover_blueprints("src/swarm/blueprints")
    assert "chucks_angels" in discovered
    assert "Chuck's Angels" not in discovered
    assert "chatbot" in discovered
    assert "ChatbotBlueprint" not in discovered
    assert "dynamic_team" in discovered
    assert "dynamic-team" in discovered  # intentional programmatic slug alias


def test_discover_supports_deprecated_and_status_flags(tmp_path: Path):
    """Test that deprecated and status metadata are extracted (for future filtering/warnings)."""
    bp_root = tmp_path / "blueprints"
    bp_root.mkdir()

    # Deprecated one
    dep_dir = bp_root / "deprecated_bp"
    dep_dir.mkdir()
    (dep_dir / "blueprint_deprecated_bp.py").write_text('''
from swarm.core.blueprint_base import BlueprintBase
class DeprecatedBp(BlueprintBase):
    """Deprecated example."""
    metadata = {
        "name": "Deprecated Example",
        "deprecated": True,
        "status": "incomplete",
        "description": "This one is deprecated for testing.",
    }
    async def run(self, messages):
        yield {"type": "message", "role": "assistant", "content": "deprecated"}
''')

    discovered = discover_blueprints(str(bp_root))
    assert "deprecated_bp" in discovered
    meta = discovered["deprecated_bp"]["metadata"]
    assert meta.get("deprecated") is True
    assert meta.get("status") == "incomplete"
