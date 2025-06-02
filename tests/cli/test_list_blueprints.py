"""
Test case for the list_blueprints command.
"""

from unittest.mock import patch, MagicMock
from swarm.extensions.cli.commands.list_blueprints import execute
# Assuming DiscoveredBlueprintInfo and BlueprintMetadata are accessible for type hinting if needed
# from swarm.core.blueprint_discovery import DiscoveredBlueprintInfo, BlueprintMetadata

class MockBlueprintClass:
    """A mock class to act as a blueprint class type."""
    pass

def test_execute(capsys):
    """Test the execute function with the new metadata structure."""
    
    # Mock the return value of discover_blueprints
    # It returns a dict mapping blueprint keys (dir names) to DiscoveredBlueprintInfo
    mock_discover_return = {
        "blueprint1_key": {
            "class_type": MockBlueprintClass, # A mock class
            "metadata": {
                "name": "Test Blueprint One",
                "abbreviation": "bp1",
                "version": "1.0.0",
                "description": "This is the first test blueprint.",
                "author": "Tester"
            }
        },
        "blueprint2_key": {
            "class_type": MockBlueprintClass,
            "metadata": {
                "name": "Second Test Blueprint",
                "abbreviation": "bp2",
                "version": "0.9.beta",
                "description": "Another test blueprint for listing.",
                # Author can be optional
            }
        },
        "blueprint_minimal": { # A blueprint with minimal metadata
            "class_type": MockBlueprintClass,
            "metadata": {
                "name": "Minimal BP" 
                # Other fields will use fallbacks or 'N/A'
            }
        }
    }

    # Patch discover_blueprints within the scope of list_blueprints.py
    with patch(
        "swarm.extensions.cli.commands.list_blueprints.discover_blueprints",
        return_value=mock_discover_return,
    ):
        # Also patch list_blueprints_from_source to directly return our mock,
        # to avoid dealing with its internal path logic in this unit test.
        # Or, ensure discover_blueprints is the correct target if list_blueprints_from_source
        # is simple enough or also mocked. For this test, patching discover_blueprints
        # which is called by list_blueprints_from_source is fine.
        execute()

    captured = capsys.readouterr()
    output = captured.out
    
    print(f"Captured output:\n{output}") # For debugging if assertions fail

    assert "Attempting to list blueprints..." in output
    assert f"Found {len(mock_discover_return)} blueprint(s):" in output

    # Check for blueprint1_key details
    assert "Key/ID: blueprint1_key" in output
    assert "Name: Test Blueprint One" in output
    assert "Abbreviation: bp1" in output
    assert "Version: 1.0.0" in output
    assert "Author: Tester" in output
    assert "Description: This is the first test blueprint." in output

    # Check for blueprint2_key details
    assert "Key/ID: blueprint2_key" in output
    assert "Name: Second Test Blueprint" in output
    assert "Abbreviation: bp2" in output
    assert "Version: 0.9.beta" in output
    assert "Author: N/A" in output # Fallback for missing author
    assert "Description: Another test blueprint for listing." in output

    # Check for blueprint_minimal details (fallbacks)
    assert "Key/ID: blueprint_minimal" in output
    assert "Name: Minimal BP" in output
    assert "Abbreviation: N/A" in output
    assert "Version: N/A" in output
    assert "Author: N/A" in output
    assert "Description: No description available." in output

def test_execute_no_blueprints(capsys):
    """Test the execute function when no blueprints are found."""
    with patch(
        "swarm.extensions.cli.commands.list_blueprints.discover_blueprints",
        return_value={}, # Empty dict signifies no blueprints found
    ):
        execute()
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Attempting to list blueprints..." in output
    assert "No blueprints found." in output
    assert "Found 0 blueprint(s):" not in output # Ensure the "Found X" message isn't there

def test_execute_discovery_exception(capsys):
    """Test the execute function when discover_blueprints raises an exception."""
    with patch(
        "swarm.extensions.cli.commands.list_blueprints.discover_blueprints",
        side_effect=Exception("Discovery failed badly!"),
    ):
        execute()
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Attempting to list blueprints..." in output
    assert "An error occurred while trying to list blueprints: Discovery failed badly!" in output
