# Handles configuration management workflows (e.g., LLM, MCP servers)

from swarm.core import config_loader
from swarm.core import config_manager
from swarm.core import server_config

def add_llm(model_name, api_key):
    """Add a new LLM configuration."""
    config = config_loader.load_server_config()
    if "llms" not in config:
        config["llms"] = {}
    config["llms"][model_name] = {"api_key": api_key}
    config_manager.save_server_config(config)
    print(f"Added LLM '{model_name}' to configuration.")
