# src/swarm/extensions/config/config_manager.py

import json
import shutil
import sys
import logging
from typing import Any, Dict

from swarm.core.server_config import load_server_config, save_server_config
from swarm.utils.color_utils import color_text
from swarm.settings import DEBUG
from swarm.core.utils.logger import *
from swarm.extensions.cli.utils import (
    prompt_user,
    log_and_exit,
    display_message
)

# Initialize logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

CONFIG_BACKUP_SUFFIX = ".backup"

def resolve_placeholders(config):
    # Recursively resolve placeholders in the config dict (env vars, etc.)
    import os
    import re
    pattern = re.compile(r'\$\{([^}]+)\}')
    def _resolve(val):
        if isinstance(val, str):
            def replacer(match):
                var = match.group(1)
                return os.environ.get(var, match.group(0))
            return pattern.sub(replacer, val)
        elif isinstance(val, dict):
            return {k: _resolve(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_resolve(v) for v in val]
        return val
    return _resolve(config)

def backup_configuration(config_path: str) -> None:
    """
    Create a backup of the existing configuration file.

    Args:
        config_path (str): Path to the configuration file.
    """
    backup_path = config_path + CONFIG_BACKUP_SUFFIX
    try:
        shutil.copy(config_path, backup_path)
        logger.info(f"Configuration backup created at '{backup_path}'")
        display_message(f"Backup of configuration created at '{backup_path}'", "info")
    except Exception as e:
        logger.error(f"Failed to create configuration backup: {e}")
        display_message(f"Failed to create backup: {e}", "error")
        sys.exit(1)

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load the server configuration from a JSON file and resolve placeholders.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        Dict[str, Any]: The resolved configuration.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the file contains invalid JSON or unresolved placeholders.
    """
    try:
        with open(config_path, "r") as file:
            config = json.load(file)
            logger.debug(f"Raw configuration loaded: {config}")
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}")
        display_message(f"Configuration file not found at {config_path}", "error")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file {config_path}: {e}")
        display_message(f"Invalid JSON in configuration file {config_path}: {e}", "error")
        sys.exit(1)

    # Resolve placeholders recursively
    try:
        resolved_config = resolve_placeholders(config)
        logger.debug(f"Configuration after resolving placeholders: {resolved_config}")
    except Exception as e:
        logger.error(f"Failed to resolve placeholders in configuration: {e}")
        display_message(f"Failed to resolve placeholders in configuration: {e}", "error")
        sys.exit(1)

    return resolved_config

def save_config(config_path: str, config: Dict[str, Any]) -> None:
    """
    Save the updated configuration to the config file.

    Args:
        config_path (str): Path to the configuration file.
        config (Dict[str, Any]): Configuration dictionary to save.

    Raises:
        SystemExit: If saving the configuration fails.
    """
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        logger.info(f"Configuration saved to '{config_path}'")
        display_message(f"Configuration saved to '{config_path}'", "info")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        display_message(f"Failed to save configuration: {e}", "error")
        sys.exit(1)

def add_llm(config_path: str) -> None:
    """
    Add a new LLM to the configuration.

    Args:
        config_path (str): Path to the configuration file.
    """
    config = load_config(config_path)
    display_message("Starting the process to add a new LLM.", "info")

    while True:
        llm_name = prompt_user("Enter the name of the new LLM (or type 'done' to finish)").strip()
        display_message(f"User entered LLM name: {llm_name}", "info")
        if llm_name.lower() == 'done':
            display_message("Finished adding LLMs.", "info")
            break
        if not llm_name:
            display_message("LLM name cannot be empty.", "error")
            continue

        if llm_name in config.get("llm", {}):
            display_message(f"LLM '{llm_name}' already exists.", "warning")
            continue

        llm = {}
        llm["provider"] = prompt_user("Enter the provider type (e.g., 'openai', 'ollama')").strip()
        llm["model"] = prompt_user("Enter the model name (e.g., 'gpt-4')").strip()
        llm["base_url"] = prompt_user("Enter the base URL for the API").strip()
        llm_api_key_input = prompt_user("Enter the environment variable for the API key (e.g., 'OPENAI_API_KEY') or leave empty if not required").strip()
        if llm_api_key_input:
            llm["api_key"] = f"${{{llm_api_key_input}}}"
        else:
            llm["api_key"] = ""
        try:
            temperature_input = prompt_user("Enter the temperature (e.g., 0.7)").strip()
            llm["temperature"] = float(temperature_input)
        except ValueError:
            display_message("Invalid temperature value. Using default 0.7.", "warning")
            llm["temperature"] = 0.7

        config.setdefault("llm", {})[llm_name] = llm
        logger.info(f"Added LLM '{llm_name}' to configuration.")
        display_message(f"LLM '{llm_name}' added.", "info")

    backup_configuration(config_path)
    save_config(config_path, config)
    display_message("LLM configuration process completed.", "info")

def remove_llm(config_path: str, llm_name: str) -> None:
    """
    Remove an existing LLM from the configuration.

    Args:
        config_path (str): Path to the configuration file.
        llm_name (str): Name of the LLM to remove.
    """
    config = load_config(config_path)

    if llm_name not in config.get("llm", {}):
        display_message(f"LLM '{llm_name}' does not exist.", "error")
        return

    confirm = prompt_user(f"Are you sure you want to remove LLM '{llm_name}'? (yes/no)").strip().lower()
    if confirm not in ['yes', 'y']:
        display_message("Operation cancelled.", "warning")
        return

    del config["llm"][llm_name]
    backup_configuration(config_path)
    save_config(config_path, config)
    display_message(f"LLM '{llm_name}' has been removed.", "info")
    logger.info(f"Removed LLM '{llm_name}' from configuration.")

def add_mcp_server(config_path: str) -> None:
    """
    Add a new MCP server to the configuration.

    Args:
        config_path (str): Path to the configuration file.
    """
    config = load_config(config_path)
    display_message("Starting the process to add a new MCP server.", "info")

    while True:
        server_name = prompt_user("Enter the name of the new MCP server (or type 'done' to finish)").strip()
        display_message(f"User entered MCP server name: {server_name}", "info")
        if server_name.lower() == 'done':
            display_message("Finished adding MCP servers.", "info")
            break
        if not server_name:
            display_message("Server name cannot be empty.", "error")
            continue

        if server_name in config.get("mcpServers", {}):
            display_message(f"MCP server '{server_name}' already exists.", "warning")
            continue

        server = {}
        server["command"] = prompt_user("Enter the command to run the MCP server (e.g., 'npx', 'uvx')").strip()
        args_input = prompt_user("Enter the arguments as a JSON array (e.g., [\"-y\", \"server-name\"])").strip()
        try:
            server["args"] = json.loads(args_input)
            if not isinstance(server["args"], list):
                raise ValueError
        except ValueError:
            display_message("Invalid arguments format. Using an empty list.", "warning")
            server["args"] = []

        env_vars = {}
        add_env = prompt_user("Do you want to add environment variables? (yes/no)").strip().lower()
        while add_env in ['yes', 'y']:
            env_var = prompt_user("Enter the environment variable name").strip()
            env_value = prompt_user(f"Enter the value or placeholder for '{env_var}' (e.g., '${{{env_var}_KEY}}')").strip()
            if env_var and env_value:
                env_vars[env_var] = env_value
            add_env = prompt_user("Add another environment variable? (yes/no)").strip().lower()

        server["env"] = env_vars

        config.setdefault("mcpServers", {})[server_name] = server
        logger.info(f"Added MCP server '{server_name}' to configuration.")
        display_message(f"MCP server '{server_name}' added.", "info")

    backup_configuration(config_path)
    save_config(config_path, config)
    display_message("MCP server configuration process completed.", "info")

def remove_mcp_server(config_path: str, server_name: str) -> None:
    """
    Remove an existing MCP server from the configuration.

    Args:
        config_path (str): Path to the configuration file.
        server_name (str): Name of the MCP server to remove.
    """
    config = load_config(config_path)

    if server_name not in config.get("mcpServers", {}):
        display_message(f"MCP server '{server_name}' does not exist.", "error")
        return

    confirm = prompt_user(f"Are you sure you want to remove MCP server '{server_name}'? (yes/no)").strip().lower()
    if confirm not in ['yes', 'y']:
        display_message("Operation cancelled.", "warning")
        return

    del config["mcpServers"][server_name]
    backup_configuration(config_path)
    save_config(config_path, config)
    display_message(f"MCP server '{server_name}' has been removed.", "info")
    logger.info(f"Removed MCP server '{server_name}' from configuration.")
