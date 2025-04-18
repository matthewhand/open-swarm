"""
Command: list_blueprints
Description: Lists all blueprints available in the system.
"""

from pathlib import Path
from swarm.core.blueprint_discovery import discover_blueprints

# Metadata for dynamic registration
description = "Lists all blueprints available in the system."
usage = "list_blueprints"

def list_blueprints():
    """Returns a list of blueprints."""
    blueprints_dir = Path(__file__).resolve().parent.parent.parent / "blueprints"
    return discover_blueprints([str(blueprints_dir)])

def execute():
    """Execute the command to list blueprints."""
    blueprints = list_blueprints()
    for blueprint_id, metadata in blueprints.items():
        print(f"Blueprint ID: {blueprint_id}, Title: {metadata.get('title', 'No title')}")
