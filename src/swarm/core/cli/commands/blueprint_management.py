from swarm.core.blueprint_utils import list_blueprints

def execute():
    """Manage blueprints (list, add, remove, etc)."""
    print("Blueprints:")
    for bp in list_blueprints():
        print(f"- {bp}")
