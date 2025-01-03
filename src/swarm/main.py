# src/swarm/main.py

import argparse
import asyncio
import json
import logging
import os
import sys
import random
import shlex

from dotenv import load_dotenv

from typing import Any, Dict, List, Optional

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    logging.debug(f"Added '{project_root}' to sys.path")

# Load environment variables from the project root
dotenv_path = os.path.join(project_root, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.debug(f"Loaded environment variables from '{dotenv_path}'")
else:
    logging.warning(f"'.env' file not found at '{dotenv_path}'")

# Import custom modules with corrected paths
try:
    from swarm.utils.logger import setup_logger
    from swarm.extensions.config.setup_wizard import run_setup_wizard
    from swarm.extensions.config.config_loader import (
        load_server_config,
        validate_and_select_llm_provider,
        inject_env_vars,
        validate_api_keys,
        are_required_mcp_servers_running,
    )
    from swarm.extensions.blueprint import discover_blueprints
    from swarm.extensions.blueprint import prompt_user_to_select_blueprint
    from swarm.extensions.blueprint.modes.cli_mode import run_cli_mode
    from swarm.extensions.blueprint.modes.rest_mode import run_rest_mode
    # from swarm.extensions.blueprint.modes.mcp_host_mode import run_mcp_host_mode  # Uncomment when implemented
    from swarm.agent.agent_builder import build_agent_with_mcp_tools
    from swarm.utils.color_utils import color_text, initialize_colorama
    logging.debug("Successfully imported custom modules")
except ImportError as e:
    logging.error(f"Error importing custom modules: {e}")
    sys.exit(1)

# Initialize logger
logger = setup_logger(__name__)
logger.info("Logger initialized")

# Mapping of LLM providers to their respective API key environment variables
LLM_PROVIDER_API_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "ollama": "OLLAMA_API_KEY",
    # Add other providers and their API key environment variables here
}

def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for dynamic LLM configuration and other overrides.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Run Open Swarm MCP in various modes.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["cli", "rest", "mcp-host"],
        default="cli",
        help="Select the mode to run the MCP (cli, rest, mcp-host). Default is 'cli'."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(project_root, "swarm_config.json"),
        help="Path to the MCP server configuration file."
    )
    parser.add_argument(
        "--llm-provider",
        type=str,
        choices=list(LLM_PROVIDER_API_KEY_MAP.keys()),
        help="Override the LLM provider specified in the config."
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        help="Override the LLM model specified in the config."
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Override the LLM temperature specified in the config."
    )
    parser.add_argument(
        "--blueprint",
        type=str,
        action='append',
        help="Specify one or more blueprints to load (can be used multiple times)."
    )
    parser.add_argument(
        "--setup",
        action='store_true',
        help="Re-run the setup wizard regardless of existing configuration."
    )
    return parser.parse_args()

def merge_llm_config(config: Dict[str, Any], selected_llm: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """
    Merge LLM configuration from command-line arguments into the existing config.

    Args:
        config (Dict[str, Any]): Existing configuration dictionary.
        selected_llm (Dict[str, Any]): Selected LLM provider configuration.
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
        Dict[str, Any]: Updated configuration with overrides.
    """
    logger.debug("Merging LLM configuration from command-line arguments")
    llm_config = config.get("llm_providers", {}).get(selected_llm['profile'], {})
    if args.llm_provider:
        llm_config["provider"] = args.llm_provider
        logger.info(f"Overridden LLM provider: {args.llm_provider}")
    if args.llm_model:
        llm_config["model"] = args.llm_model
        logger.info(f"Overridden LLM model: {args.llm_model}")
    if args.temperature is not None:
        llm_config["temperature"] = args.temperature
        logger.info(f"Overridden LLM temperature: {args.temperature}")

    config["llm_providers"][selected_llm['profile']] = llm_config
    logger.debug(f"Final LLM configuration after merge: {llm_config}")
    return config

async def configure_missing_mcp_servers(
    missing_servers: List[str],
    config: Dict[str, Any],
    blueprint_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Configure missing MCP servers dynamically based on blueprint metadata.

    Args:
        missing_servers (List[str]): List of missing MCP server names.
        config (Dict[str, Any]): Current configuration dictionary.
        blueprint_metadata (Dict[str, Any]): Metadata of the current blueprint.

    Returns:
        Dict[str, Any]: Updated configuration dictionary with missing MCP servers configured.
    """
    logger.debug(f"Configuring missing MCP servers: {missing_servers}")
    mcp_servers = config.get("mcpServers", {})
    for server in missing_servers:
        logger.info(f"Configuring MCP Server: {server}")
        print(color_text(f"\nConfiguring MCP Server: {server}", "cyan"))
        server_config = mcp_servers.get(server, {})
        if not server_config:
            server_config = {}
            mcp_servers[server] = server_config
            logger.debug(f"Initialized configuration for MCP server '{server}'")

        # Command
        current_command = server_config.get("command", "")
        default_command = "uvx" if server != "brave-search" else "npx"
        prompt_cmd = f"Enter the command for '{server}' [default: {default_command}]: "
        user_command = input(prompt_cmd).strip() or default_command
        server_config["command"] = user_command
        logger.debug(f"Set command for MCP server '{server}': {user_command}")

        # Args
        default_args = blueprint_metadata.get("default_args", "")
        prompt_args = f"Enter the arguments for '{server}' [default: {default_args}]: "
        user_args_input = input(prompt_args).strip()
        if user_args_input:
            new_args = shlex.split(user_args_input)
            server_config["args"] = new_args
            logger.debug(f"Set custom args for MCP server '{server}': {new_args}")
        else:
            server_config["args"] = shlex.split(default_args)
            logger.debug(f"Set default args for MCP server '{server}': {server_config['args']}")

        # Environment Variables
        env_vars = blueprint_metadata.get("env_vars", [])
        for env_var in env_vars:
            env_value = server_config.get("env", {}).get(env_var, "")
            if not env_value:
                prompt_env = f"Enter the value for environment variable '{env_var}' (will be set as '{env_var}'): "
                user_env_value = input(prompt_env).strip()
                if user_env_value:
                    server_config.setdefault("env", {})[env_var] = user_env_value
                    # Suggest adding to .env file
                    add_to_env = input(f"Would you like to add '{env_var}' to your .env file? (yes/no): ").strip().lower()
                    if add_to_env in ['yes', 'y']:
                        try:
                            with open(os.path.join(project_root, ".env"), "a") as env_file:
                                env_file.write(f"\n{env_var}={user_env_value}\n")
                            print(color_text(f"{env_var} has been added to your .env file.", "green"))
                            logger.info(f"Added environment variable '{env_var}' to '.env' file")
                        except Exception as e:
                            logger.error(f"Failed to write to .env file: {e}")
                            print(color_text(f"Failed to write to .env file. Please add '{env_var}' manually.", "red"))
        mcp_servers[server] = server_config
        logger.debug(f"Updated configuration for MCP server '{server}': {server_config}")

    config['mcpServers'] = mcp_servers
    logger.info("Completed configuration of missing MCP servers")
    return config

def save_configuration(config_path: str, config: Dict[str, Any]):
    """
    Save the updated configuration to the config file, excluding sensitive API keys.

    Args:
        config_path (str): Path to the configuration file.
        config (Dict[str, Any]): Configuration dictionary to save.
    """
    logger.debug(f"Saving configuration to '{config_path}'")
    try:
        safe_config = config.copy()
        # Remove LLM API Key from config
        for profile in safe_config.get('llm_providers', {}):
            if 'api_key' in safe_config['llm_providers'][profile]:
                safe_config['llm_providers'][profile]['api_key'] = ""
                logger.debug(f"Removed LLM API key from profile '{profile}' in configuration for security")
        # Remove MCP server API keys from env
        for srv in safe_config.get('mcpServers', {}):
            if 'env' in safe_config['mcpServers'][srv]:
                for env_var in safe_config['mcpServers'][srv]['env']:
                    safe_config['mcpServers'][srv]['env'][env_var] = ""
                    logger.debug(f"Removed MCP server environment variable '{env_var}' from server '{srv}' in configuration for security")
        with open(config_path, "w") as f:
            json.dump(safe_config, f, indent=4)
        print(color_text("\nConfiguration has been saved successfully! Remember to set your API keys in the .env file.\n", "green"))
        logger.info(f"Configuration saved to '{config_path}'")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        print(color_text("Failed to save configuration. Please check permissions.", "red"))

async def run_blueprint_mode(
    blueprints: List[str],
    config: Dict[str, Any],
    blueprints_metadata: Dict[str, Dict[str, Any]],
    args: argparse.Namespace
):
    """
    Run specified blueprints.

    Args:
        blueprints (List[str]): List of blueprints to run.
        config (Dict[str, Any]): Configuration dictionary.
        blueprints_metadata (Dict[str, Dict[str, Any]]): Metadata of all discovered blueprints.
        args (argparse.Namespace): Parsed command-line arguments.
    """
    logger.debug(f"Running blueprint mode with blueprints: {blueprints}")
    if not blueprints:
        logger.error("No blueprints specified.")
        print(color_text("No blueprints specified.", "red"))
        return

    for blueprint in blueprints:
        if blueprint not in blueprints_metadata:
            logger.error(f"Blueprint '{blueprint}' not found.")
            print(color_text(f"Blueprint '{blueprint}' not found.", "red"))
            continue

        blueprint_metadata = blueprints_metadata[blueprint]
        logger.debug(f"Blueprint metadata for '{blueprint}': {blueprint_metadata}")
        required_servers = blueprint_metadata.get("required_mcp_servers", [])
        logger.debug(f"Blueprint '{blueprint}' requires MCP servers: {required_servers}")

        all_running, missing_servers = are_required_mcp_servers_running(required_servers, config)
        logger.debug(f"Are all required MCP servers running? {all_running}")
        if not all_running:
            print(color_text(
                f"\nBlueprint '{blueprint}' requires the following MCP servers to be configured: {', '.join(missing_servers)}", 
                "yellow"
            ))
            print(color_text(
                "Some required MCP servers are missing or improperly configured.", 
                "yellow"
            ))
            configure_missing = input("Would you like to configure the missing MCP servers now? (yes/no): ").strip().lower()
            logger.debug(f"User chose to configure missing MCP servers: {configure_missing}")
            if configure_missing in ['yes', 'y']:
                config = await configure_missing_mcp_servers(missing_servers, config, blueprint_metadata)
                save_configuration(args.config, config)
            else:
                print(color_text("Cannot proceed without configuring the required MCP servers.", "red"))
                logger.warning("User declined to configure missing MCP servers")
                continue

        try:
            logger.debug("Building agent with MCP tools")
            agent = build_agent_with_mcp_tools(config)  # Synchronously build the agent
            logger.info(f"Agent built successfully for blueprint '{blueprint}' with MCP tools")
        except Exception as e:
            logger.error(f"Failed to build agent for blueprint '{blueprint}': {e}")
            print(color_text(f"Failed to build agent for blueprint '{blueprint}': {e}", "red"))
            continue

        if args.mode == "rest":
            logger.debug(f"Running in REST mode for blueprint '{blueprint}'")
            await run_rest_mode(agent, blueprint)
        elif args.mode == "mcp-host":
            # await run_mcp_host_mode(agent)
            logger.error("MCP host mode is not implemented yet")
            print(color_text("MCP host mode is not implemented yet", "red"))
        else:
            logger.debug(f"Running in CLI mode for blueprint '{blueprint}'")
            await run_cli_mode(agent, colorama_available=True)

def handle_shutdown():
    """
    Perform cleanup operations before shutdown.
    """
    logger.info("Shutting down Open Swarm MCP...")
    # Add any cleanup operations here

async def main():
    """
    Main entry point for the Open Swarm MCP application.
    """
    initialize_colorama()
    logger.debug("Starting main application")
    args = parse_arguments()
    logger.debug(f"Command-line arguments: {args}")
    blueprints_metadata = discover_blueprints([os.path.join(project_root, "blueprints")])
    logger.debug(f"Discovered blueprints metadata: {blueprints_metadata}")

    # Handle configuration setup
    if args.setup:
        logger.info("Setup flag detected. Running setup wizard.")
        config = run_setup_wizard(args.config, blueprints_metadata)
    else:
        try:
            config = load_server_config(args.config)
            logger.info(f"Configuration file detected at '{args.config}'. Loading configuration.")
            logger.debug(f"Loaded configuration: {config}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Configuration issue ({e}). Launching setup wizard.")
            config = run_setup_wizard(args.config, blueprints_metadata)
        else:
            selected_llm = validate_and_select_llm_provider(config)
            config = inject_env_vars(config)
            config = validate_api_keys(config, selected_llm)
            logger.debug(f"Configuration after LLM provider selection and validation: {config}")

    # Handle LLM API key setup
    llm_config = config.get("llm_providers", {}).get(os.getenv("LLM", "default"), {})
    llm_provider = llm_config.get("provider", "openai")
    expected_api_key_env_var = LLM_PROVIDER_API_KEY_MAP.get(llm_provider, "LLM_API_KEY")
    logger.debug(f"LLM provider: {llm_provider}")
    llm_api_key = llm_config.get("api_key", "")
    logger.debug(f"LLM API Key from config: {'set' if llm_api_key else 'not set'}")

    if llm_api_key:
        logger.info(f"LLM API Key loaded from configuration for provider '{llm_provider}'.")
    else:
        print(color_text(
            f"LLM API Key is missing for provider '{llm_provider}'. Please set the '{expected_api_key_env_var}' environment variable.", 
            "yellow"
        ))
        logger.warning(f"LLM API Key is missing for provider '{llm_provider}'. Please set the '{expected_api_key_env_var}' environment variable.")

    # Determine which blueprints to load
    if args.blueprint:
        blueprints_to_load = args.blueprint  # List of blueprints specified via command-line
        logger.debug(f"Blueprints specified via --blueprint: {blueprints_to_load}")
    else:
        blueprints_to_load = list(blueprints_metadata.keys())  # Load all available blueprints
        logger.debug("No --blueprint specified. Loading all available blueprints.")

    # Run in the specified mode
    if args.mode in ["rest", "mcp-host"]:
        logger.debug(f"Operating in '{args.mode}' mode")
        await run_blueprint_mode(blueprints_to_load, config, blueprints_metadata, args)
    elif args.mode == "cli":
        logger.debug("Operating in 'cli' mode")
        if not blueprints_to_load:
            print(color_text("\nNo blueprints specified. Prompting to select a blueprint.\n", "cyan"))
            selected_blueprint = prompt_user_to_select_blueprint(blueprints_metadata)
            if selected_blueprint:
                blueprints_to_load = [selected_blueprint]
                logger.debug(f"Selected blueprint after selection prompt: '{selected_blueprint}'")
            else:
                print(color_text("No blueprint selected. Exiting.", "red"))
                logger.warning("No blueprint selected. Exiting.")
                return
        await run_blueprint_mode(blueprints_to_load, config, blueprints_metadata, args)
    else:
        logger.error(f"Unsupported mode: {args.mode}")
        print(color_text(f"Unsupported mode: {args.mode}", "red"))

if __name__ == "__main__":
    try:
        logger.debug("Starting asyncio event loop")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nReceived shutdown signal (Ctrl+C)")
        logger.info("Received shutdown signal (Ctrl+C)")
        handle_shutdown()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        print(color_text(f"\nFatal error: {e}", "red"))
        handle_shutdown()
        sys.exit(1)
    finally:
        logger.info("Application terminated")
        sys.exit(0)
