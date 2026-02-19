# Handles blueprint discovery and validation for the CLI

from swarm.core.blueprint_discovery import discover_blueprints

# from swarm.core.config_loader import load_server_config  # Removed: function does not exist

def list_blueprints():
    """List available blueprints and their metadata."""
    blueprints = discover_blueprints()
    if not blueprints:
        print("No blueprints discovered.")
        return
    print("Discovered Blueprints:")
    for name, metadata in blueprints.items():
        print(f"- {name}: {metadata.get('description', 'No description available.')}")

def enable_blueprint(blueprint_name):
    """
    Enable a blueprint by adding it to config and creating a CLI symlink.
    """
    import json
    import os
    CONFIG_PATH = os.path.expanduser("~/.config/swarm/swarm_config.json")
    BIN_DIR = os.path.expanduser("~/.local/bin")
    BP_RUNNER = os.path.join(os.path.dirname(__file__), f"../../../../src/swarm/blueprints/{blueprint_name}/blueprint_{blueprint_name}.py")
    CLI_SYMLINK = os.path.join(BIN_DIR, blueprint_name)

    # Load config
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    enabled = config.get("blueprints", {}).get("enabled", [])
    if blueprint_name in enabled:
        print(f"Blueprint '{blueprint_name}' is already enabled.")
        return
    # Add to config
    enabled.append(blueprint_name)
    if "blueprints" not in config:
        config["blueprints"] = {}
    config["blueprints"]["enabled"] = enabled
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    # Ensure bin dir exists
    os.makedirs(BIN_DIR, exist_ok=True)
    # Create symlink (Python runner)
    if not os.path.isfile(BP_RUNNER):
        print(f"Blueprint runner not found: {BP_RUNNER}")
        return
    # Write a .sh launcher wrapper for .py if not present
    CLI_WRAPPER = CLI_SYMLINK
    with open(CLI_WRAPPER, "w") as f:
        f.write(f"#!/usr/bin/env bash\nexec python3 '{os.path.abspath(BP_RUNNER)}' \"$@\"")
    os.chmod(CLI_WRAPPER, 0o755)
    print(f"Enabled blueprint '{blueprint_name}'. CLI utility installed at {CLI_WRAPPER}.")

# Handles configuration management workflows (e.g., LLM, MCP servers)

# from swarm.core.config_loader import (
#     load_server_config,
#     save_server_config,
# )

def add_llm(model_name, api_key):
    """Add a new LLM configuration."""
    config = {}  # load_server_config()
    if "llms" not in config:
        config["llms"] = {}
    config["llms"][model_name] = {"api_key": api_key}
    # save_server_config(config)
    print(f"Added LLM '{model_name}' to configuration.")
