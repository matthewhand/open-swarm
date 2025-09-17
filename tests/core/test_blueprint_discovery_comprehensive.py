"""
Comprehensive tests for blueprint discovery and loading functionality.
These tests verify the core mechanisms that allow the system to find and load blueprints.
"""

import os
import tempfile
from pathlib import Path

import pytest

from swarm.core.blueprint_discovery import discover_blueprints


class TestBlueprintDiscoveryComprehensive:
    """High-value tests for blueprint discovery functionality."""

    def test_discover_blueprints_finds_all_core_blueprints(self):
        """Test that blueprint discovery finds all core blueprints with correct metadata."""
        # When: discovering blueprints from the core blueprints directory
        blueprint_dir = "src/swarm/blueprints"
        blueprints = discover_blueprints(blueprint_dir)
        
        # Then: we should find a substantial number of blueprints
        assert len(blueprints) > 10, f"Expected >10 blueprints, found {len(blueprints)}"
        
        # And: each blueprint should have required metadata
        for name, blueprint_info in blueprints.items():
            assert 'metadata' in blueprint_info, f"Blueprint {name} missing metadata"
            metadata = blueprint_info['metadata']
            assert 'name' in metadata, f"Blueprint {name} missing name in metadata"
            assert 'description' in metadata, f"Blueprint {name} missing description in metadata"
            # Note: The metadata name may differ from the key (e.g., "Chuck's Angels" vs "chucks_angels")

    def test_discover_blueprints_handles_malformed_blueprints_gracefully(self):
        """Test that discovery gracefully handles malformed or incomplete blueprints."""
        # Given: a temporary directory with a malformed blueprint
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a malformed blueprint file
            malformed_blueprint = temp_path / "malformed_blueprint.py"
            malformed_blueprint.write_text("""
# This is a malformed blueprint - missing required classes
SOME_CONSTANT = "value"
def some_function():
    pass
""")
            
            # When: discovering blueprints (should not crash)
            # Note: We're testing that this doesn't raise an exception
            try:
                # This should not crash even with malformed blueprints
                blueprints = discover_blueprints(str(temp_path))
                # If we get here, the test passes - it handled the malformed blueprint gracefully
            except Exception as e:
                pytest.fail(f"Discovery should handle malformed blueprints gracefully, but raised: {e}")

    def test_discover_blueprints_respects_directory_structure(self):
        """Test that blueprint discovery correctly maps directory structure to blueprint names."""
        # When: discovering blueprints
        blueprint_dir = "src/swarm/blueprints"
        blueprints = discover_blueprints(blueprint_dir)
        
        # Then: we should find blueprints with expected naming patterns
        blueprint_names = set(blueprints.keys())
        
        # Check for some expected core blueprints
        expected_patterns = ['chatbot', 'jeeves', 'geese', 'codey', 'poets']
        found_patterns = [pattern for pattern in expected_patterns if any(pattern in name for name in blueprint_names)]
        
        assert len(found_patterns) >= 3, f"Expected to find at least 3 of {expected_patterns}, found {found_patterns}"

    def test_blueprint_metadata_includes_essential_fields(self):
        """Test that all discovered blueprints have essential metadata fields."""
        # When: discovering blueprints
        blueprint_dir = "src/swarm/blueprints"
        blueprints = discover_blueprints(blueprint_dir)
        
        # Then: each blueprint should have complete metadata
        essential_fields = ['name', 'description']  # version is optional in some blueprints
        
        for name, blueprint_info in blueprints.items():
            metadata = blueprint_info['metadata']
            for field in essential_fields:
                assert field in metadata, f"Blueprint {name} missing essential field '{field}'"
                assert metadata[field], f"Blueprint {name} has empty value for field '{field}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])