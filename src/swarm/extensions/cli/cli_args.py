# src/swarm/extensions/blueprint/modes/cli_mode/cli_args.py

import argparse
import os
import sys
from typing import Namespace

# --- DEBUG PRINTS REMOVED BY CASCADE ---
# print(f"[DEBUG] cli_args.py startup: sys.argv={sys.argv}")
# print(f"[DEBUG] cli_args.py startup: LITELLM_MODEL={os.environ.get('LITELLM_MODEL')}, DEFAULT_LLM={os.environ.get('DEFAULT_LLM')}")

def parse_arguments() -> Namespace:
    """
    Parse command-line arguments for dynamic LLM configuration, MCP server management, and other overrides.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Run Open Swarm MCP in various modes or manage configurations."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subparser for running modes
    run_parser = subparsers.add_parser("run", help="Run Open Swarm MCP in various modes.")
    run_parser.add_argument(
        "--mode",
        type=str,
        choices=["cli", "rest", "mcp-host"],
        default="cli",
        help="Select the mode to run the MCP (cli, rest, mcp-host). Default is 'cli'."
    )
    run_parser.add_argument(
        "--config",
        type=str,
        default=None,  # Will be set dynamically in main.py
        help="Path to the MCP server configuration file."
    )
    run_parser.add_argument(
        "--llm",
        type=str,
        help="Override the LLM specified in the config."
    )
    run_parser.add_argument(
        "--llm-model",
        type=str,
        help="Override the LLM model specified in the config."
    )
    run_parser.add_argument(
        "--temperature",
        type=float,
        help="Override the LLM temperature specified in the config."
    )
    run_parser.add_argument(
        "--blueprint",
        type=str,
        action='append',
        help="Specify one or more blueprints to load (can be used multiple times)."
    )
    run_parser.add_argument(
        "--setup",
        action='store_true',
        help="Re-run the setup wizard regardless of existing configuration."
    )

    # Subparser for configuration management
    config_parser = subparsers.add_parser("config", help="Manage Swarm MCP configurations.")
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Configuration commands")

    # Add LLM
    add_llm_parser = config_subparsers.add_parser("add-llm", help="Add a new LLM.")
    # No additional arguments; will use interactive prompts

    # Remove LLM
    remove_llm_parser = config_subparsers.add_parser("remove-llm", help="Remove an existing LLM.")
    remove_llm_parser.add_argument(
        "llm_name",
        type=str,
        help="Name of the LLM to remove."
    )

    # Add MCP server
    add_server_parser = config_subparsers.add_parser("add-server", help="Add a new MCP server.")
    # No additional arguments; will use interactive prompts

    # Remove MCP server
    remove_server_parser = config_subparsers.add_parser("remove-server", help="Remove an existing MCP server.")
    remove_server_parser.add_argument(
        "server_name",
        type=str,
        help="Name of the MCP server to remove."
    )

    return parser.parse_args()
