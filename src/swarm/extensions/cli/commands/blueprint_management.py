# Handles blueprint discovery and validation for the CLI

from swarm.core.blueprint_discovery import discover_blueprints
from swarm.core.config_loader import load_server_config

def list_blueprints():
    """List available blueprints and their metadata."""
    blueprints = discover_blueprints()
    if not blueprints:
        print("No blueprints discovered.")
        return
    print("Discovered Blueprints:")
    for name, metadata in blueprints.items():
        print(f"- {name}: {metadata.get('description', 'No description available.')}")

cat > src/swarm/extensions/cli/commands/config_management.py << 'EOF'
# Handles configuration management workflows (e.g., LLM, MCP servers)

from swarm.core.config_loader import (
    load_server_config,
    save_server_config,
)

def add_llm(model_name, api_key):
    """Add a new LLM configuration."""
    config = load_server_config()
    if "llms" not in config:
        config["llms"] = {}
    config["llms"][model_name] = {"api_key": api_key}
    save_server_config(config)
    print(f"Added LLM '{model_name}' to configuration.")
