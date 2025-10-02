from pathlib import Path
from swarm.core.blueprint_discovery import discover_blueprints


def execute():
    """Manage blueprints (list, add, remove, etc)."""
    print("Blueprints:")
    blueprint_dir = Path(__file__).resolve().parent.parent.parent / "blueprints"
    for bp in discover_blueprints(str(blueprint_dir)).keys():
        print(f"- {bp}")
